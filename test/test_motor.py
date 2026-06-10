import unittest

from flowlamp_rpi.devices.motor import DynamixelConfig, MotorController


class MotorControllerTest(unittest.TestCase):
    def setUp(self):
        self.controller = MotorController(
            DynamixelConfig(max_velocity=5),
        )

    def test_default_configuration_uses_only_working_motors(self):
        self.assertEqual(self.controller.config.motor_ids, (1, 4))
        self.assertEqual(DynamixelConfig().max_velocity, 20)
        self.assertFalse(DynamixelConfig().enable_soft_limits)
        self.assertEqual(DynamixelConfig().vertical_velocity_multiplier, 2.0)

    def test_move_xy_maps_horizontal_and_vertical_axes(self):
        result = self.controller.move_xy(0.5, -1.0, speed=4)

        self.assertEqual(set(result), {1, 4})
        self.assertEqual(result[1]["goal_velocity"], 2)
        self.assertEqual(result[4]["goal_velocity"], 5)

    def test_move_xyz_ignores_depth_axis(self):
        result = self.controller.move_xyz(0.0, 0.5, -1.0, speed=4)

        self.assertEqual(set(result), {1, 4})
        self.assertEqual(result[1]["goal_velocity"], 0)
        self.assertEqual(result[4]["goal_velocity"], -2)


if __name__ == "__main__":
    unittest.main()
