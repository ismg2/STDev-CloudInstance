import unittest

from app.cloud_api import CloudAPIError, validate_benchmark_options


class TestBenchmarkOptionValidation(unittest.TestCase):
    def test_rejects_st_neural_art_on_non_npu_board(self):
        with self.assertRaises(CloudAPIError):
            validate_benchmark_options(
                board_name="STM32H747I-DISCO",
                st_neural_art="default",
            )

    def test_rejects_memory_pool_on_npu_board(self):
        with self.assertRaises(CloudAPIError):
            validate_benchmark_options(
                board_name="STM32N6570-DK",
                target="stm32n6",
                memory_pool="pool.json",
            )

    def test_accepts_cpu_mode_on_npu_board(self):
        validate_benchmark_options(
            board_name="STM32N6570-DK",
            target="stm32",
            split_weights=True,
            allocate_activations=True,
            allocate_states=False,
        )

    def test_accepts_basic_options_on_regular_stm32_board(self):
        validate_benchmark_options(
            board_name="STM32H747I-DISCO",
            target="stm32",
            split_weights=True,
            allocate_activations=True,
            allocate_states=True,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

