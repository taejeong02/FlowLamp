import 'package:flutter/material.dart';

class LampControlTab extends StatefulWidget {
  const LampControlTab({super.key});

  @override
  State<LampControlTab> createState() => _LampControlTabState();
}

class _LampControlTabState extends State<LampControlTab> {
  // 램프 상태 관리 변수들
  bool isOn = true;
  double brightness = 80;
  double red = 255;
  double green = 128;
  double blue = 64;

  @override
  Widget build(BuildContext context) {
    // RGB 값으로 색상 생성
    Color currentColor = Color.fromRGBO(red.toInt(), green.toInt(), blue.toInt(), 1.0);

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
                Text(isOn ? "LAMP ON" : "LAMP OFF", 
                     style: const TextStyle(fontWeight: FontWeight.bold)),
                Switch(value: isOn, activeColor: Colors.amber, onChanged: (v) => setState(() => isOn = v)),
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
            ),
          ),

          // 3. RGB 색상 조절 카드
          _buildControlCard(
            title: "LED 색상 (RGB)",
            child: Column(
              children: [
                _buildRgbSlider("R", red, Colors.red, (v) => setState(() => red = v)),
                _buildRgbSlider("G", green, Colors.green, (v) => setState(() => green = v)),
                _buildRgbSlider("B", blue, Colors.blue, (v) => setState(() => blue = v)),
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
              boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 10)],
            ),
            child: Center(
              child: Text(
                "#${currentColor.value.toRadixString(16).substring(2).toUpperCase()}",
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
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
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: TextStyle(color: Colors.grey.shade600, fontSize: 12)),
          const SizedBox(height: 10),
          child,
        ],
      ),
    );
  }

  // RGB 슬라이더 생성기 (💡 에러 해결 완료: SizedBox 사용)
  Widget _buildRgbSlider(String label, double value, Color color, Function(double) onChanged) {
    return Row(
      children: [
        Text(label, style: TextStyle(fontWeight: FontWeight.bold, color: color)),
        Expanded(
          child: Slider(
            value: value,
            max: 255,
            activeColor: color,
            onChanged: onChanged,
          ),
        ),
        SizedBox(
          width: 30,
          child: Text(
            value.toInt().toString(), 
            textAlign: TextAlign.center,
          ),
        ),
      ],
    );
  }
}