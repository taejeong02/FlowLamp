import 'package:flutter/material.dart';

class Tab4Manual extends StatefulWidget {
  const Tab4Manual({super.key});

  @override
  State<Tab4Manual> createState() => _Tab4ManualState();
}

class _Tab4ManualState extends State<Tab4Manual> {
  bool postureMode = false;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        // 4개의 모터 제어 패널 생성
        ...List.generate(4, (index) => _buildMotorControlPanel(index + 1)),
        
        const SizedBox(height: 20),
        
        // 자세 모드 스위치
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 5),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(20),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withOpacity(0.05),
                blurRadius: 10,
                offset: const Offset(0, 4),
              ),
            ],
          ),
          child: SwitchListTile(
            contentPadding: EdgeInsets.zero,
            title: const Text("자세 모드 (카메라 연동)", style: TextStyle(fontWeight: FontWeight.bold)),
            value: postureMode,
            activeColor: Colors.amber,
            onChanged: (v) => setState(() => postureMode = v),
          ),
        ),
      ],
    );
  }

  // 💡 요청하신 < 모터 이름 > 스타일의 가로형 제어 패널
  Widget _buildMotorControlPanel(int motorNum) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween, // 💡 좌우로 넓게 배치
        children: [
          // 왼쪽 버튼
          IconButton(
            icon: const Icon(Icons.chevron_left_rounded, size: 32),
            color: Colors.amber.shade700,
            onPressed: () => print("$motorNum번 모터 왼쪽"),
          ),
          
          // 중앙 모터 이름
          Text(
            "$motorNum번 모터", 
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)
          ),
          
          // 오른쪽 버튼
          IconButton(
            icon: const Icon(Icons.chevron_right_rounded, size: 32),
            color: Colors.amber.shade700,
            onPressed: () => print("$motorNum번 모터 오른쪽"),
          ),
        ],
      ),
    );
  }
}