import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:http/http.dart' as http; // 👈 통신용 패키지 추가

class FocusTimerSection extends StatefulWidget {
  const FocusTimerSection({Key? key}) : super(key: key);

  @override
  State<FocusTimerSection> createState() => _FocusTimerSectionState();
}

class _FocusTimerSectionState extends State<FocusTimerSection> {
  // 1. 디폴트 시간을 00:00 (0초)로 변경
  int initialTimeInSeconds = 0; 
  int remainingTimeInSeconds = 0; 
  bool isRunning = false; 
  Timer? _timer;

  // ⚠️ 중요: 나중에 라즈베리 파이가 연결된 실제 Wi-Fi IP 주소로 변경해야 합니다.
final String rpiUrl = "http://127.0.0.1:8000";

  String get formattedTime {
    int minutes = remainingTimeInSeconds ~/ 60;
    int seconds = remainingTimeInSeconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  double get progress {
    if (initialTimeInSeconds == 0) return 0.0;
    return remainingTimeInSeconds / initialTimeInSeconds;
  }

  // 👉 라즈베리 파이에 종료 신호를 쏘는 함수 추가
  Future<void> _sendAlertSignal() async {
    try {
      final url = Uri.parse('$rpiUrl/timer/done');
      final response = await http.post(url);
      if (response.statusCode == 200) {
        print("서버에 타이머 종료 신호 전송 성공!");
      }
    } catch (e) {
      print("통신 실패: $e");
    }
  }

  void startTimer() {
    if (_timer != null) _timer!.cancel();
    setState(() { isRunning = true; });
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        if (remainingTimeInSeconds > 0) {
          remainingTimeInSeconds--;
          
          // 2. 시간이 0이 되는 순간 처리
          if (remainingTimeInSeconds == 0) {
            timer.cancel();
            isRunning = false;
            
            // 💡 앱 알림창을 띄우는 동시에 라즈베리 파이로 조명 깜빡임 신호 전송!
            _sendAlertSignal(); 
            _showTimeUpDialog(); 
          }
        } else {
          timer.cancel();
          isRunning = false;
        }
      });
    });
  }

  void pauseTimer() {
    if (_timer != null) _timer!.cancel();
    setState(() { isRunning = false; });
  }

  void toggleTimer() {
    if (isRunning) {
      pauseTimer();
    } else if (remainingTimeInSeconds > 0) {
      startTimer();
    } else {
      // 시간 설정이 00:00일 때 재생을 누르면 시간 설정창을 띄워주는 UX 센스!
      _selectTime(context);
    }
  }

  // 3. 시간 종료 알림창 함수
  void _showTimeUpDialog() {
    showDialog(
      context: context,
      barrierDismissible: false, // 바깥 영역 터치로 닫히지 않게 (확인 버튼을 누르도록)
      builder: (BuildContext context) {
        return AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20.0)),
          title: const Row(
            children: [
              Icon(Icons.alarm_on, color: Colors.amber, size: 28),
              SizedBox(width: 10),
              Text('시간 종료!', style: TextStyle(fontWeight: FontWeight.bold)),
            ],
          ),
          content: const Text(
            '설정한 집중 시간이 끝났습니다.\n램프 조명 알림이 작동합니다.',
            style: TextStyle(height: 1.5),
          ),
          actions: [
            TextButton(
              onPressed: () {
                Navigator.pop(context); // 창 닫기
              },
              child: const Text('확인', style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold, fontSize: 16)),
            ),
          ],
        );
      },
    );
  }

  Future<void> _selectTime(BuildContext context) async {
    bool wasRunning = isRunning;
    if (wasRunning) pauseTimer();

    Duration tempDuration = Duration(seconds: initialTimeInSeconds);

    await showDialog(
      context: context,
      builder: (BuildContext builder) {
        return Dialog(
          backgroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20.0)),
          child: SizedBox(
            height: 300,
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      TextButton(
                        onPressed: () => Navigator.pop(context),
                        child: const Text('취소', style: TextStyle(color: Colors.grey, fontSize: 16)),
                      ),
                      TextButton(
                        onPressed: () {
                          setState(() {
                            if (tempDuration.inSeconds > 0) {
                              initialTimeInSeconds = tempDuration.inSeconds;
                              remainingTimeInSeconds = tempDuration.inSeconds;
                            }
                          });
                          Navigator.pop(context);
                        },
                        child: const Text('확인', style: TextStyle(color: Colors.black, fontSize: 16, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                ),
                const Divider(),
                Expanded(
                  child: CupertinoTimerPicker(
                    mode: CupertinoTimerPickerMode.hms,
                    initialTimerDuration: tempDuration,
                    onTimerDurationChanged: (Duration newDuration) {
                      tempDuration = newDuration;
                    },
                  ),
                ),
              ],
            ),
          ),
        );
      },
    ).then((_) {
      if (wasRunning && remainingTimeInSeconds > 0) startTimer();
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Stack(
          alignment: Alignment.center,
          clipBehavior: Clip.none,
          children: [
            SizedBox(
              width: 220,
              height: 220,
              child: CircularProgressIndicator(
                value: progress,
                strokeWidth: 12,
                color: Colors.yellow.shade600,
                backgroundColor: Colors.grey.shade200,
                strokeCap: StrokeCap.round,
              ),
            ),
            GestureDetector(
              onTap: () => _selectTime(context),
              child: Container(
                color: Colors.transparent,
                padding: const EdgeInsets.all(40.0),
                child: Text(
                  formattedTime,
                  style: TextStyle(
                    fontSize: 56, 
                    color: Colors.grey.shade700, 
                    fontWeight: FontWeight.bold
                  ),
                ),
              ),
            ),
            Positioned(
              bottom: -16, 
              child: GestureDetector(
                onTap: toggleTimer,
                child: Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white,
                    boxShadow: [
                      BoxShadow(color: Colors.black.withOpacity(0.15), blurRadius: 10, offset: const Offset(0, 4)),
                    ],
                  ),
                  child: Icon(
                    isRunning ? Icons.pause_rounded : Icons.play_arrow_rounded,
                    color: Colors.grey.shade700,
                    size: 36,
                  ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 40),
        Text(
          "FOCUS",
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, letterSpacing: 1.5, color: Colors.grey.shade800),
        ),
      ],
    );
  }
}