import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';

import '../services/flowlamp_api.dart';

class FocusTimerSection extends StatefulWidget {
  const FocusTimerSection({super.key});

  @override
  State<FocusTimerSection> createState() => _FocusTimerSectionState();
}

class _FocusTimerSectionState extends State<FocusTimerSection> {
  int initialTimeInSeconds = 0;
  int remainingTimeInSeconds = 0;
  bool isRunning = false;
  Timer? _timer;
  final FlowLampApi _api = FlowLampApi();

  String get formattedTime {
    int minutes = remainingTimeInSeconds ~/ 60;
    int seconds = remainingTimeInSeconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  double get progress => initialTimeInSeconds == 0
      ? 0.0
      : remainingTimeInSeconds / initialTimeInSeconds;

  Future<void> _sendAlertSignal() async {
    try {
      await _api.notifyTimerDone();
    } catch (e) {
      debugPrint("통신 에러: $e");
    }
  }

  void startTimer() {
    if (_timer != null) _timer!.cancel();
    setState(() => isRunning = true);
    _timer = Timer.periodic(const Duration(seconds: 1), (timer) {
      setState(() {
        if (remainingTimeInSeconds > 0) {
          remainingTimeInSeconds--;
          if (remainingTimeInSeconds == 0) {
            timer.cancel();
            isRunning = false;
            _sendAlertSignal();
            _showTimeUpDialog();
          }
        }
      });
    });
  }

  void toggleTimer() {
    if (isRunning) {
      _timer?.cancel();
      setState(() => isRunning = false);
    } else if (remainingTimeInSeconds > 0) {
      startTimer();
    } else {
      _selectTime(context);
    }
  }

  // 💡 더 세련된 알림창 디자인
  void _showTimeUpDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
        child: Container(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.check_circle_outline,
                color: Colors.amber,
                size: 64,
              ),
              const SizedBox(height: 20),
              const Text(
                "집중 완료!",
                style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 10),
              const Text(
                "램프가 집중 시간 종료를 알립니다.",
                style: TextStyle(color: Colors.grey),
              ),
              const SizedBox(height: 30),
              ElevatedButton(
                onPressed: () => Navigator.pop(context),
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.amber,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 40,
                    vertical: 12,
                  ),
                ),
                child: const Text("확인"),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _selectTime(BuildContext context) async {
    Duration tempDuration = Duration(seconds: initialTimeInSeconds);
    await showDialog(
      context: context,
      builder: (context) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        child: SizedBox(
          height: 300,
          child: Column(
            children: [
              Expanded(
                child: CupertinoTimerPicker(
                  mode: CupertinoTimerPickerMode.ms,
                  initialTimerDuration: tempDuration,
                  onTimerDurationChanged: (d) => tempDuration = d,
                ),
              ),
              TextButton(
                onPressed: () {
                  setState(() {
                    initialTimeInSeconds = tempDuration.inSeconds;
                    remainingTimeInSeconds = tempDuration.inSeconds;
                  });
                  Navigator.pop(context);
                },
                child: const Text(
                  "설정 완료",
                  style: TextStyle(fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Stack(
          alignment: Alignment.center,
          children: [
            //
            Padding(
              padding: const EdgeInsets.all(12.0),
              child: SizedBox(
                width: 210,
                height: 210,
                child: CircularProgressIndicator(
                  value: progress,
                  strokeWidth: 10,
                  color: Colors.amber,
                  backgroundColor: Colors.grey.shade200,
                ),
              ),
            ),
            GestureDetector(
              onTap: () => _selectTime(context),
              child: Text(
                formattedTime,
                style: const TextStyle(
                  fontSize: 52,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            Positioned(
              bottom: 0,
              child: GestureDetector(
                onTap: toggleTimer,
                child: Container(
                  width: 50,
                  height: 50,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white,
                    boxShadow: [
                      BoxShadow(color: Colors.black12, blurRadius: 10),
                    ],
                  ),
                  child: Icon(
                    isRunning ? Icons.pause : Icons.play_arrow,
                    size: 30,
                  ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 40),
        const Text(
          "FOCUS",
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
            letterSpacing: 2,
          ),
        ),
      ],
    );
  }
}
