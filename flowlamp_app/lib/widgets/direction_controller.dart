import 'package:flutter/material.dart';

class DirectionControllerScreen extends StatelessWidget {
  const DirectionControllerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F5), // 배경색
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new, color: Colors.black87),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // 방향 제어 패드 위젯
              _buildDPad(context),
              
              const SizedBox(height: 50),
              
              // 하단 텍스트
              const Text(
                '램프 방향 제어',
                style: TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87,
                ),
              ),
              const SizedBox(height: 50), // 하단 여백 조절
            ],
          ),
        ),
      ),
    );
  }

  // 원형 D-Pad를 구성하는 위젯 분리
  Widget _buildDPad(BuildContext context) {
    return Container(
      width: 250,
      height: 250,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: Colors.white,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 15,
            spreadRadius: 5,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          // 상단 화살표
          Positioned(
            top: 15,
            child: _buildArrowButton(Icons.arrow_drop_up, () {
              print("Up pressed");
              // 여기에 상단 이동 로직 추가
            }),
          ),
          // 하단 화살표
          Positioned(
            bottom: 15,
            child: _buildArrowButton(Icons.arrow_drop_down, () {
              print("Down pressed");
              // 여기에 하단 이동 로직 추가
            }),
          ),
          // 좌측 화살표
          Positioned(
            left: 15,
            child: _buildArrowButton(Icons.arrow_left, () {
              print("Left pressed");
              // 여기에 좌측 이동 로직 추가
            }),
          ),
          // 우측 화살표
          Positioned(
            right: 15,
            child: _buildArrowButton(Icons.arrow_right, () {
              print("Right pressed");
              // 여기에 우측 이동 로직 추가
            }),
          ),
          
          // 중앙 다방향 아이콘 (추후 기능 추가 가능)
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.grey.shade100,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.2),
                  blurRadius: 5,
                  offset: const Offset(0, 2),
                )
              ]
            ),
            child: const Center(
              child: Icon(Icons.open_with, size: 40, color: Colors.black87),
            ),
          )
        ],
      ),
    );
  }

  // 개별 화살표 버튼을 만드는 헬퍼 위젯
  Widget _buildArrowButton(IconData icon, VoidCallback onPressed) {
    return IconButton(
      iconSize: 50,
      padding: EdgeInsets.zero,
      icon: Icon(icon, color: Colors.grey.shade700),
      onPressed: onPressed,
    );
  }
}