import 'package:flutter/material.dart';

import '../services/flowlamp_api.dart';

class LampControlTab extends StatefulWidget {
  const LampControlTab({super.key});

  @override
  State<LampControlTab> createState() => _LampControlTabState();
}

class _LampControlTabState extends State<LampControlTab> {
  final FlowLampApi _api = FlowLampApi();
  int _colorRequestId = 0;

  // 램프 상태 관리 변수들
  bool isOn = true;
  double brightness = 80;
  double red = 255;
  double green = 128;
  double blue = 64;

  @override
  void initState() {
    super.initState();
    _loadStatus();
  }

  Future<void> _loadStatus() async {
    try {
      final status = await _api.getStatus();
      if (!mounted) return;

      final color = status['color'];
      setState(() {
        final power = status['power'];
        final nextBrightness = _numToDouble(status['brightness']);

        if (power is bool) {
          isOn = power;
        }
        if (nextBrightness != null) {
          brightness = _clampDouble(nextBrightness, 0, 100);
        }
        if (color is Map) {
          red = _clampDouble(_numToDouble(color['r']) ?? red, 0, 255);
          green = _clampDouble(_numToDouble(color['g']) ?? green, 0, 255);
          blue = _clampDouble(_numToDouble(color['b']) ?? blue, 0, 255);
        }
      });
    } catch (error) {
      debugPrint('FlowLamp status error: $error');
    }
  }

  Future<void> _setPower(bool value) async {
    final previous = isOn;
    setState(() => isOn = value);

    try {
      final response = await _api.setPower(value);
      if (!mounted) return;

      final power = response['power'];
      if (power is bool) {
        setState(() => isOn = power);
      }
    } catch (error) {
      debugPrint('FlowLamp power error: $error');
      if (mounted) {
        setState(() => isOn = previous);
      }
    }
  }

  Future<void> _sendBrightness(double value) async {
    try {
      final response = await _api.setBrightness(value.round());
      if (!mounted) return;

      final nextBrightness = _numToDouble(response['brightness']);
      if (nextBrightness != null) {
        setState(() => brightness = _clampDouble(nextBrightness, 0, 100));
      }
    } catch (error) {
      debugPrint('FlowLamp brightness error: $error');
    }
  }

  Future<void> _sendColor() async {
    final requestId = ++_colorRequestId;
    try {
      final response = await _api.setColor(
        red: red.round(),
        green: green.round(),
        blue: blue.round(),
      );
      if (!mounted || requestId != _colorRequestId) return;

      final color = response['color'];
      if (color is Map) {
        setState(() {
          red = _clampDouble(_numToDouble(color['r']) ?? red, 0, 255);
          green = _clampDouble(_numToDouble(color['g']) ?? green, 0, 255);
          blue = _clampDouble(_numToDouble(color['b']) ?? blue, 0, 255);
        });
      }
    } catch (error) {
      debugPrint('FlowLamp color error: $error');
    }
  }

  double? _numToDouble(Object? value) {
    if (value is num) {
      return value.toDouble();
    }
    return null;
  }

  double _clampDouble(double value, num min, num max) {
    return value.clamp(min, max).toDouble();
  }

  @override
  Widget build(BuildContext context) {
    // RGB 값으로 색상 생성
    Color currentColor = Color.fromRGBO(
      red.toInt(),
      green.toInt(),
      blue.toInt(),
      1.0,
    );

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 1. 램프 상태 제어 카드
          _buildControlCard(
            title: "램프 상태",
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Icon(Icons.lightbulb_outline, color: Colors.amber),
                Text(
                  isOn ? "LAMP ON" : "LAMP OFF",
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
                Switch(
                  value: isOn,
                  activeColor: Colors.amber,
                  onChanged: _setPower,
                ),
              ],
            ),
          ),

          // 2. 밝기 조절 카드
          _buildControlCard(
            title: "밝기 조절",
            child: Slider(
              value: brightness,
              max: 100,
              activeColor: Colors.amber,
              onChanged: (v) => setState(() => brightness = v),
              onChangeEnd: _sendBrightness,
            ),
          ),

          // 3. RGB 색상 조절 카드
          _buildControlCard(
            title: "LED 색상 (RGB)",
            child: Column(
              children: [
                _buildRgbSlider(
                  "R",
                  red,
                  Colors.red,
                  (v) => setState(() => red = v),
                ),
                _buildRgbSlider(
                  "G",
                  green,
                  Colors.green,
                  (v) => setState(() => green = v),
                ),
                _buildRgbSlider(
                  "B",
                  blue,
                  Colors.blue,
                  (v) => setState(() => blue = v),
                ),
              ],
            ),
          ),

          // 4. 색상 미리보기 영역
          const Text("색상 미리보기", style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 10),
          Container(
            height: 100,
            width: double.infinity,
            decoration: BoxDecoration(
              color: currentColor,
              borderRadius: BorderRadius.circular(16),
              boxShadow: const [
                BoxShadow(color: Colors.black12, blurRadius: 10),
              ],
            ),
            child: Center(
              child: Text(
                "#${currentColor.value.toRadixString(16).substring(2).toUpperCase()}",
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // 카드 형태의 레이아웃 위젯
  Widget _buildControlCard({required String title, required Widget child}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 20),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(color: Colors.grey.shade600, fontSize: 12),
          ),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }

  // RGB 슬라이더 생성기 (💡 에러 해결 완료: SizedBox 사용)
  Widget _buildRgbSlider(
    String label,
    double value,
    Color color,
    Function(double) onChanged,
  ) {
    return Row(
      children: [
        Text(
          label,
          style: TextStyle(fontWeight: FontWeight.bold, color: color),
        ),
        Expanded(
          child: Slider(
            value: value,
            max: 255,
            activeColor: color,
            onChanged: onChanged,
            onChangeEnd: (_) => _sendColor(),
          ),
        ),
        SizedBox(
          width: 30,
          child: Text(value.toInt().toString(), textAlign: TextAlign.center),
        ),
      ],
    );
  }
}
