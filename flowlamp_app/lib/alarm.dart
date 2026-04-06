import 'package:flutter/material.dart';
import 'widgets/focus_timer.dart';
import 'widgets/night_mode_card.dart';

class AlarmScreen extends StatelessWidget {
  const AlarmScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F5), 
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leadingWidth: 64, 
        leading: Align(
          alignment: Alignment.center,
          child: IconButton(
            icon: const Icon(Icons.arrow_back_ios_new, color: Colors.black87),
            splashRadius: 24, 
            onPressed: () {
              Navigator.pop(context);
            },
          ),
        ),
      ),
      // 💡 여기서부터 변경: SingleChildScrollView를 없애고 화면에 꽉 차는 Column 사용
      body: SafeArea(
        child: Column(
          children: [
            // 1. 집중 타이머 영역 (전체 세로 화면의 약 45% 할당)
            Expanded(
              flex: 45,
              child: Center( // 화면 중앙 정렬
                // 💡 핵심: FittedBox가 화면 크기에 맞춰 내용물을 안전하게 축소시킵니다.
                child: FittedBox(
                  fit: BoxFit.scaleDown, 
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 20.0),
                    child: const FocusTimerSection(),
                  ),
                ),
              ),
            ),
            
            // 2. 야간 모드 카드 영역 (전체 세로 화면의 약 55% 할당)
            Expanded(
              flex: 55,
              child: Center(
                // 💡 핵심: 여기도 FittedBox를 적용하여 에러 방지
                child: FittedBox(
                  fit: BoxFit.scaleDown,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 10.0),
                    child: const NightModeCard(),
                  ),
                ),
              ),
            ),
            
            const SizedBox(height: 20), // 맨 아래쪽 최소한의 여백
          ],
        ),
      ),
    );
  }
}