import unittest

from marketplace_agent import reserve_inventory, run_checkout_step


class CheckoutStepTest(unittest.TestCase):
    def test_checkout_step_returns_action_result(self):
        self.assertEqual(
            run_checkout_step("reserve-inventory", lambda: reserve_inventory("sku-7")),
            "reserved:sku-7",
        )
