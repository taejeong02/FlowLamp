import 'dart:async';

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../services/flowlamp_api.dart';

class FocusTimerSection extends StatefulWidget {
  const FocusTimerSection({super.key});

  @override
  State<FocusTimerSection> createState() => _FocusTimerSectionState();
}

class _FocusTimerSectionState extends State<FocusTimerSection> {
  final FlowLampApi _api = FlowLampApi();

  int initialTimeInSeconds = 0;
  int remainingTimeInSeconds = 0;
  bool isRunning = false;
  Timer? _timer;

  String get formattedTime {
    final minutes = remainingTimeInSeconds ~/ 60;
    final seconds = remainingTimeInSeconds % 60;
    return '${minutes.toString().padLeft(2, '0')}:${seconds.toString().padLeft(2, '0')}';
  }

  double get progress {
    if (initialTimeInSeconds == 0) return 0.0;
    return remainingTimeInSeconds / initialTimeInSeconds;
  }

  Future<void> _sendAlertSignal() async {
    try {
      await _api.notifyTimerDone();
      print('Timer done signal sent');
    } catch (error) {
      print('Timer done signal failed: $error');
    }
  }

  void startTimer() {
    _timer?.cancel();
    setState(() {
      isRunning = true;
    });

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
        } else {
          timer.cancel();
          isRunning = false;
        }
      });
    });
  }

  void pauseTimer() {
    _timer?.cancel();
    setState(() {
      isRunning = false;
    });
  }

  void toggleTimer() {
    if (isRunning) {
      pauseTimer();
    } else if (remainingTimeInSeconds > 0) {
      startTimer();
    } else {
      _selectTime(context);
    }
  }

  void _showTimeUpDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return AlertDialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20.0),
          ),
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
                Navigator.pop(context);
              },
              child: const Text(
                '확인',
                style: TextStyle(
                  color: Colors.black,
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Future<void> _selectTime(BuildContext context) async {
    final wasRunning = isRunning;
    if (wasRunning) pauseTimer();

    var tempDuration = Duration(seconds: initialTimeInSeconds);

    await showDialog(
      context: context,
      builder: (BuildContext builder) {
        return Dialog(
          backgroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(20.0),
          ),
          child: SizedBox(
            height: 300,
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16.0,
                    vertical: 12.0,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      TextButton(
                        onPressed: () => Navigator.pop(context),
                        child: const Text(
                          '취소',
                          style: TextStyle(color: Colors.grey, fontSize: 16),
                        ),
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
                        child: const Text(
                          '확인',
                          style: TextStyle(
                            color: Colors.black,
                            fontSize: 16,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
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
                    fontWeight: FontWeight.bold,
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
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.15),
                        blurRadius: 10,
                        offset: const Offset(0, 4),
                      ),
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
          'FOCUS',
          style: TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w600,
            letterSpacing: 1.5,
            color: Colors.grey.shade800,
          ),
        ),
      ],
    );
  }
}
