import 'package:flutter/material.dart';

import 'alarm.dart';
import 'services/flowlamp_api.dart';
import 'widgets/alarmbutton.dart';
import 'widgets/anglebutton.dart';
import 'widgets/brightslider.dart';
import 'widgets/colorslider.dart';
import 'widgets/direction_controller.dart';
import 'widgets/powerbutton.dart';
import 'widgets/sleepbutton.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flow Lamp',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),
      ),
      home: const MyHomePage(title: 'Flow_Lamp'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title, this.api});

  final String title;
  final FlowLampApi? api;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  late final FlowLampApi _api;

  bool isOn = false;
  bool _isStatusLoading = true;
  bool _isPowerLoading = false;
  bool _isColorLoading = false;
  double sliderValue = 0;
  double brightness = 50;

  @override
  void initState() {
    super.initState();
    _api = widget.api ?? FlowLampApi();
    _loadLampStatus();
  }

  Future<void> _loadLampStatus() async {
    setState(() {
      _isStatusLoading = true;
    });

    try {
      final response = await _api.getStatus();
      if (!mounted) return;
      setState(() {
        isOn = response['is_on'] as bool? ?? false;
        sliderValue = _sliderValueFromColor(response['color']) ?? sliderValue;
      });
    } catch (error) {
      _showLampError('Failed to load lamp status', error);
    } finally {
      if (mounted) {
        setState(() {
          _isStatusLoading = false;
        });
      }
    }
  }

  Future<void> _setPower(bool nextValue) async {
    if (_isPowerLoading) return;

    setState(() {
      _isPowerLoading = true;
    });

    try {
      final response = await _api.setPower(nextValue);
      if (!mounted) return;
      setState(() {
        isOn = response['is_on'] as bool? ?? nextValue;
      });
    } catch (error) {
      _showLampError('Failed to change lamp power', error);
    } finally {
      if (mounted) {
        setState(() {
          _isPowerLoading = false;
        });
      }
    }
  }

  Future<void> _setColorFromSlider(double value) async {
    if (_isColorLoading) return;

    final color = _rgbFromSliderValue(value);
    setState(() {
      _isColorLoading = true;
    });

    try {
      final response = await _api.setColor(
        red: color.red,
        green: color.green,
        blue: color.blue,
      );
      if (!mounted) return;
      setState(() {
        sliderValue = _sliderValueFromColor(response['color']) ?? value;
      });
    } catch (error) {
      _showLampError('Failed to change lamp color', error);
    } finally {
      if (mounted) {
        setState(() {
          _isColorLoading = false;
        });
      }
    }
  }

  void _showLampError(String message, Object error) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text('$message: $error')));
  }

  ({int red, int green, int blue}) _rgbFromSliderValue(double value) {
    final hue = (value.clamp(0.0, 100.0).toDouble() / 100 * 360) % 360;
    final x = 1 - ((hue / 60) % 2 - 1).abs();

    final (red, green, blue) = switch (hue) {
      < 60 => (1.0, x, 0.0),
      < 120 => (x, 1.0, 0.0),
      < 180 => (0.0, 1.0, x),
      < 240 => (0.0, x, 1.0),
      < 300 => (x, 0.0, 1.0),
      _ => (1.0, 0.0, x),
    };

    return (
      red: _toColorChannel(red),
      green: _toColorChannel(green),
      blue: _toColorChannel(blue),
    );
  }

  int _toColorChannel(double value) {
    return (value * 255).round().clamp(0, 255).toInt();
  }

  double? _sliderValueFromColor(Object? color) {
    if (color is! List || color.length < 3) return null;

    final red = _asColorRatio(color[0]);
    final green = _asColorRatio(color[1]);
    final blue = _asColorRatio(color[2]);
    if (red == null || green == null || blue == null) return null;

    final maxValue = [red, green, blue].reduce((a, b) => a > b ? a : b);
    final minValue = [red, green, blue].reduce((a, b) => a < b ? a : b);
    final delta = maxValue - minValue;
    if (delta == 0) return null;

    final hue = switch (maxValue) {
      _ when maxValue == red => 60 * (((green - blue) / delta) % 6),
      _ when maxValue == green => 60 * (((blue - red) / delta) + 2),
      _ => 60 * (((red - green) / delta) + 4),
    };

    return ((hue + 360) % 360) / 360 * 100;
  }

  double? _asColorRatio(Object? value) {
    if (value is! num) return null;
    return value.clamp(0, 255) / 255;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Flow Lamp'),
        actions: [
          IconButton(
            tooltip: 'Refresh status',
            onPressed: _isStatusLoading || _isPowerLoading
                ? null
                : _loadLampStatus,
            icon: _isStatusLoading
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh),
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.only(top: 60, bottom: 32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.start,
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              PowerButton(
                isOn: isOn,
                isLoading: _isStatusLoading || _isPowerLoading,
                onTap: () {
                  _setPower(!isOn);
                },
              ),
              ColorSlider(
                value: sliderValue,
                isEnabled: !_isColorLoading,
                onChanged: (value) {
                  setState(() {
                    sliderValue = value;
                  });
                },
                onChangeEnd: _setColorFromSlider,
              ),
              BrightnessSlider(
                value: brightness,
                onChanged: (value) {
                  setState(() {
                    brightness = value;
                  });
                },
              ),
              const SleepingButton(),
              Row(
                children: [
                  Expanded(
                    child: InkWell(
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => const AlarmScreen(),
                          ),
                        );
                      },
                      child: const AlarmCard(),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: InkWell(
                      onTap: () {
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) =>
                                const DirectionControllerScreen(),
                          ),
                        );
                      },
                      child: const AngleCard(),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
