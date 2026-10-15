# *******************************************************************************
# Copyright (c) 2026 Contributors to the Eclipse Foundation
#
# See the NOTICE file(s) distributed with this work for additional
# information regarding copyright ownership.
#
# This program and the accompanying materials are made available under the
# terms of the Apache License Version 2.0 which is available at
# https://www.apache.org/licenses/LICENSE-2.0
#
# SPDX-License-Identifier: Apache-2.0
# *******************************************************************************

"""Tests for multiprocessing batch preprocessing."""

import queue
import unittest
from pathlib import Path
from queue import Queue
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from score.parsers.franca_parser.preprocessor.batch_runner import (
    BatchPreProcessError,
    BatchRunner,
    PreProcessorRunner,
    PreProcessorWorker,
    batch_preprocess,
    parse_args,
)


class BatchRunnerTest(unittest.TestCase):
    """Verify worker failures reach the parent process."""

    def test_worker_run_processes_files_in_the_current_process(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            source_file = Path(temporary_directory) / "source.fidl"
            source_file.write_text(
                "#if defined FEATURE\npackage selected\n#endif\n",
                encoding="utf-8",
            )
            input_queue: Queue = Queue()
            output_queue: Queue = Queue()
            error_queue: Queue = Queue()
            all_paths_sent = SimpleNamespace(value=False)
            input_queue.put([source_file])
            input_queue.put(None)

            worker = PreProcessorWorker(
                input_queue,
                output_queue,
                error_queue,
                all_paths_sent,
                {"FEATURE"},
                batch_size=1,
                queue_timeout=0.01,
            )
            worker.run()

        self.assertTrue(error_queue.empty(), error_queue.get_nowait() if not error_queue.empty() else None)
        self.assertEqual(output_queue.get_nowait(), [(str(source_file.resolve()), "package selected\n")])
        self.assertTrue(error_queue.empty())
        self.assertTrue(all_paths_sent.value)

    def test_worker_run_retries_empty_queue_and_flushes_partial_batch(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            source_file = Path(temporary_directory) / "source.fidl"
            source_file.write_text("package partial\n", encoding="utf-8")
            input_queue = Mock()
            input_queue.get.side_effect = [queue.Empty, [source_file], None]
            output_queue: Queue = Queue()
            error_queue: Queue = Queue()
            all_paths_sent = SimpleNamespace(value=False)

            worker = PreProcessorWorker(
                input_queue,
                output_queue,
                error_queue,
                all_paths_sent,
                set(),
                batch_size=10,
                queue_timeout=0.01,
            )
            worker.run()

            self.assertEqual(output_queue.get_nowait(), [(str(source_file.resolve()), "package partial\n")])
            self.assertTrue(error_queue.empty())

        worker = PreProcessorWorker(
            Queue(),
            Queue(),
            Queue(),
            SimpleNamespace(value=True),
            set(),
            queue_timeout=0.01,
        )
        worker.run()

    def test_preprocessor_runner_starts_and_joins_workers_in_current_process(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            source_file = Path(temporary_directory) / "source.fidl"
            source_file.write_text("package threaded\n", encoding="utf-8")
            input_queue: Queue = Queue()
            output_queue: Queue = Queue()
            error_queue: Queue = Queue()
            input_queue.put([source_file])
            input_queue.put(None)
            input_queue.put(None)

            runner = PreProcessorRunner(
                input_queue,
                output_queue,
                error_queue,
                SimpleNamespace(value=False),
                set(),
                thread_count=2,
                batch_size=1,
                queue_timeout=0.01,
            )
            runner.run()

        self.assertEqual(output_queue.get_nowait(), [(str(source_file.resolve()), "package threaded\n")])
        self.assertTrue(error_queue.empty())

    def test_worker_run_reports_bad_batches_and_flushes_partial_results(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            good_files = [Path(temporary_directory) / f"good_{index}.fidl" for index in range(3)]
            bad_files = [Path(temporary_directory) / f"bad_{index}.fidl" for index in range(2)]
            for index, good_file in enumerate(good_files):
                good_file.write_text(f"package good_{index}\n", encoding="utf-8")
            for bad_file in bad_files:
                bad_file.write_text("#else\n", encoding="utf-8")
            input_queue: Queue = Queue()
            output_queue: Queue = Queue()
            error_queue: Queue = Queue()
            input_queue.put([good_files[0], bad_files[0], good_files[1], bad_files[1], good_files[2]])
            input_queue.put(None)

            worker = PreProcessorWorker(
                input_queue,
                output_queue,
                error_queue,
                SimpleNamespace(value=False),
                set(),
                queue_timeout=0.01,
            )
            worker.run()

        self.assertEqual(
            output_queue.get_nowait(),
            [(str(path.resolve()), f"package good_{index}\n") for index, path in enumerate(good_files)],
        )
        errors = [error_queue.get_nowait(), error_queue.get_nowait()]
        self.assertTrue(error_queue.empty())
        self.assertEqual([error["exception_type"] for error in errors], ["BatchPreProcessError"] * 2)
        self.assertEqual({error["file_path"] for error in errors}, {str(path.resolve()) for path in bad_files})

    def test_worker_run_rejects_non_batch_queue_items(self) -> None:
        error_queue: Queue = Queue()
        worker = PreProcessorWorker(
            Queue(),
            Queue(),
            error_queue,
            SimpleNamespace(value=True),
            set(),
            queue_timeout=0.01,
        )
        worker.in_queue_file_list.put("not-a-batch")
        worker.run()

        error = error_queue.get_nowait()
        self.assertEqual(error["exception_type"], "ValueError")
        self.assertIn("Expected a list, tuple, or set", error["message"])

    def test_get_file_paths_reads_lists_and_directories_once(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            nested = root / "nested"
            nested.mkdir()
            first = root / "first.fidl"
            second = root / "second.fdepl"
            nested_file = nested / "nested.fsdl"
            ignored = root / "ignored.txt"
            for path in (first, second, nested_file, ignored):
                path.write_text("", encoding="utf-8")
            file_path_file = root / "files.txt"
            file_path_file.write_text(f"{first}\n{second}\n", encoding="utf-8")
            dir_path_file = root / "dirs.txt"
            dir_path_file.write_text(f"{root}\n", encoding="utf-8")

            runner = BatchRunner(
                dir_list=[root, root / "missing"],
                dir_path_file=dir_path_file,
                file_list=[first],
                file_path_file=file_path_file,
                recur=True,
            )
            runner.get_file_paths(batch_size=2, sentinel_count=2)

        batches = []
        sentinel_count = 0
        while sentinel_count < 2:
            batch = runner.out_queue_file_list.get(timeout=1)
            if batch is None:
                sentinel_count += 1
            else:
                batches.extend(batch)
        self.assertEqual(set(batches), {first.resolve(), second.resolve(), nested_file.resolve()})
        self.assertEqual(len(batches), 3)
        self.assertEqual(sentinel_count, 2)
        self.assertEqual(runner.debug_info["num_read_files"], 3)

    def test_batch_run_propagates_missing_file_path_list_error(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            missing_list = Path(temporary_directory) / "missing-files.txt"
            runner = BatchRunner(file_path_file=missing_list)

            with (
                patch("score.parsers.franca_parser.preprocessor.batch_runner.MAX_PREPROCESSOR_PROCESS_COUNT", 1),
                self.assertRaises(FileNotFoundError),
            ):
                runner.batch_run()

    def test_batch_run_propagates_directory_traversal_error(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            source_directory = Path(temporary_directory) / "sources"
            source_directory.mkdir()
            runner = BatchRunner(dir_list=[source_directory])

            with (
                patch("score.parsers.franca_parser.preprocessor.batch_runner.MAX_PREPROCESSOR_PROCESS_COUNT", 1),
                patch.object(Path, "iterdir", side_effect=PermissionError("directory traversal failed")),
                self.assertRaisesRegex(PermissionError, "directory traversal failed"),
            ):
                runner.batch_run()

    def test_batch_run_raises_for_missing_explicit_franca_file(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            missing_file = Path(temporary_directory) / "missing.fidl"
            runner = BatchRunner(file_list=[missing_file])

            with (
                patch("score.parsers.franca_parser.preprocessor.batch_runner.MAX_PREPROCESSOR_PROCESS_COUNT", 1),
                self.assertRaises(FileNotFoundError) as error_context,
            ):
                runner.batch_run()

        self.assertIn(str(missing_file), str(error_context.exception))

    def test_parse_args_and_batch_preprocess_write_debug_artifacts(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_file = root / "source.fidl"
            debug_dir = root / "debug"
            source_file.write_text("package sample\n", encoding="utf-8")
            args = ["--files", str(source_file), "--defined", "FEATURE", "--debug-output", str(debug_dir)]

            parsed = parse_args(args)
            self.assertEqual(parsed.files, [str(source_file)])
            self.assertEqual(parsed.defined, ["FEATURE"])
            self.assertEqual(parsed.debug_output, debug_dir)

            with patch("score.parsers.franca_parser.preprocessor.batch_runner.MAX_PREPROCESSOR_PROCESS_COUNT", 1):
                result = batch_preprocess(args)

            self.assertEqual(result, {str(source_file.resolve()): "package sample\n"})
            self.assertTrue((debug_dir / "franca_preprocessed_result.pkl").is_file())
            self.assertTrue((debug_dir / "example_processed_file.txt").is_file())
            self.assertTrue((debug_dir / "franca_preprocessed_log.json").is_file())

    def test_batch_run_when_worker_thread_fails_raises_after_cleanup(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            good_file = Path(temporary_directory) / "good.fidl"
            bad_file = Path(temporary_directory) / "bad.fidl"
            after_error_file = Path(temporary_directory) / "after_error.fidl"
            good_file.write_text("package good\n", encoding="utf-8")
            bad_file.write_text("#else\n", encoding="utf-8")
            after_error_file.write_text("package after_error\n", encoding="utf-8")

            processes: list[PreProcessorRunner] = []

            class RecordingPreProcessorRunner(PreProcessorRunner):
                def __init__(self, *args: object, **kwargs: object) -> None:
                    super().__init__(*args, **kwargs)
                    processes.append(self)

            runner = BatchRunner(file_list=[good_file, bad_file, after_error_file])
            with (
                patch(
                    "score.parsers.franca_parser.preprocessor.batch_runner.PreProcessorRunner",
                    RecordingPreProcessorRunner,
                ),
                patch("score.parsers.franca_parser.preprocessor.batch_runner.MAX_PREPROCESSOR_PROCESS_COUNT", 1),
                self.assertRaises(BatchPreProcessError) as error_context,
            ):
                runner.batch_run(batch_size=10)

        self.assertIn(str(bad_file.resolve()), str(error_context.exception))
        self.assertIn("Traceback (most recent call last)", str(error_context.exception))
        self.assertIn("PreProcessError: #else without previous #if", str(error_context.exception))
        self.assertRegex(str(error_context.exception), r"Process \d+, thread .+ \(ID \d+\), at .+")
        self.assertEqual(runner.debug_info["num_processed_files"], 2)
        self.assertEqual(len(processes), 1)
        self.assertFalse(processes[0].is_alive())
        self.assertEqual(processes[0].exitcode, 0)

    def test_batch_run_when_multiple_worker_threads_fail_reports_all_errors(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            bad_files = [Path(temporary_directory) / f"bad_{index}.fidl" for index in range(2)]
            for bad_file in bad_files:
                bad_file.write_text("#else\n", encoding="utf-8")

            runner = BatchRunner(file_list=bad_files)
            with (
                patch("score.parsers.franca_parser.preprocessor.batch_runner.MAX_PREPROCESSOR_PROCESS_COUNT", 1),
                self.assertRaises(BatchPreProcessError) as error_context,
            ):
                runner.batch_run(batch_size=1)

        error_message = str(error_context.exception)
        self.assertIn("2 preprocessing worker error(s) occurred", error_message)
        for bad_file in bad_files:
            self.assertIn(str(bad_file.resolve()), error_message)


if __name__ == "__main__":
    unittest.main()
