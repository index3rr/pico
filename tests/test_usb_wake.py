"""Host-side checks for explicit USB wake; no real device or credentials used."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent.parent


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UsbWakeTests(unittest.TestCase):
    def setUp(self):
        self.hardware = Mock()
        machine = types.ModuleType('machine')
        machine.USBDevice = Mock(return_value=self.hardware)
        usb = types.ModuleType('usb')
        device = types.ModuleType('usb.device')
        usb.device = device
        self.controller = Mock()
        device.get = Mock(return_value=self.controller)
        hid = types.ModuleType('usb.device.hid')
        keyboard = types.ModuleType('usb.device.keyboard')

        class Interface:
            def __init__(self, *args, **kwargs):
                pass

        hid.HIDInterface = keyboard.KeyboardInterface = Interface
        with patch.dict(sys.modules, {'machine': machine, 'usb': usb,
                                     'usb.device': device, 'usb.device.hid': hid,
                                     'usb.device.keyboard': keyboard}):
            self.usb = load_module('usb_wake_under_test',
                                   'projects/usb_control/pico_usb.py')

    def test_setup_preserves_serial_and_advertises_wake_without_input(self):
        self.usb.setup()
        self.usb.setup()
        self.controller.init.assert_called_once_with(
            self.usb.keyboard, self.usb.mouse, builtin_driver=True,
            remote_wakeup=True)
        self.hardware.remote_wakeup.assert_not_called()

    def test_wake_reports_host_result_without_sending_input(self):
        self.usb.keyboard = Mock()
        self.usb.mouse = Mock()
        for result in (True, False):
            self.hardware.remote_wakeup.return_value = result
            self.assertIs(self.usb.wake(), result)
        self.assertEqual(self.hardware.remote_wakeup.call_count, 2)
        self.usb.keyboard.assert_not_called()
        self.assertEqual(self.usb.keyboard.method_calls, [])
        self.assertEqual(self.usb.mouse.method_calls, [])

    def test_cli_wake_is_separate_from_input_and_does_not_retry_errors(self):
        cli = load_module('hid_wake_cli_under_test', 'tools/hid.py')
        with patch.object(sys, 'argv', ['hid.py', 'wake']), \
                patch.object(cli, 'request', side_effect=RuntimeError('offline')) as request, \
                patch.object(cli, 'actions') as actions, \
                contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'offline'):
                cli.main()
        request.assert_called_once_with('/api/wake', {}, None)
        actions.assert_not_called()


if __name__ == '__main__':
    unittest.main()
