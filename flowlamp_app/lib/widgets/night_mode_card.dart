import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart'; // 💡 수동 시간 설정(드럼통 픽커)을 위해 추가
import 'package:progressive_time_picker/progressive_time_picker.dart';

class NightModeCard extends StatefulWidget {
  const NightModeCard({super.key});

  @override
  State<NightModeCard> createState() => _NightModeCardState();
}

class _NightModeCardState extends State<NightModeCard> {
  bool isNightModeOn = true;
  Timer? _minuteTimer;

  PickedTime _startTime = PickedTime(h: 23, m: 0);
  PickedTime _endTime = PickedTime(h: 6, m: 0);

  @override
  void initState() {
    super.initState();
    _minuteTimer = Timer.periodic(const Duration(minutes: 1), (timer) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _minuteTimer?.cancel();
    super.dispose();
  }

  String _formatTime(PickedTime time) {
    return '${time.h.toString().padLeft(2, '0')}:${time.m.toString().padLeft(2, '0')}';
  }

  bool _isCurrentlyNightTime() {
    if (!isNightModeOn) return false;

    DateTime now = DateTime.now();
    int currentMinutes = now.hour * 60 + now.minute;
    int startMinutes = _startTime.h * 60 + _startTime.m;
    int endMinutes = _endTime.h * 60 + _endTime.m;

    if (startMinutes <= endMinutes) {
      return currentMinutes >= startMinutes && currentMinutes < endMinutes;
    } else {
      return currentMinutes >= startMinutes || currentMinutes < endMinutes;
    }
  }

  // 💡 추가된 기능: 텍스트를 눌렀을 때 뜨는 수동 시간 설정 다이얼로그
  Future<void> _showManualTimePicker(BuildContext context) async {
    DateTime now = DateTime.now();
    // 픽커 초기값을 현재 설정된 시간으로 세팅
    DateTime tempStart = DateTime(now.year, now.month, now.day, _startTime.h, _startTime.m);
    DateTime tempEnd = DateTime(now.year, now.month, now.day, _endTime.h, _endTime.m);

    await showDialog(
      context: context,
      builder: (BuildContext context) {
        return Dialog(
          backgroundColor: Colors.white,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20.0)),
          child: SizedBox(
            height: 380, // 취침/기상 시간을 위아래로 배치하기 위해 높이 확보
            child: Column(
              children: [
                // 상단 확인/취소 버튼
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
                            _startTime = PickedTime(h: tempStart.hour, m: tempStart.minute);
                            _endTime = PickedTime(h: tempEnd.hour, m: tempEnd.minute);
                          });
                          Navigator.pop(context);
                        },
                        child: const Text('확인', style: TextStyle(color: Colors.black, fontSize: 16, fontWeight: FontWeight.bold)),
                      ),
                    ],
                  ),
                ),
                const Divider(height: 1),
                
                // 1. 시작 시간(취침) 픽커 영역
                const Padding(
                  padding: EdgeInsets.only(top: 16.0, bottom: 8.0),
                  child: Text('🌙 시작 시간 설정', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.black87)),
                ),
                Expanded(
                  child: CupertinoDatePicker(
                    mode: CupertinoDatePickerMode.time,
                    use24hFormat: true, // 24시간 형식 사용
                    initialDateTime: tempStart,
                    minuteInterval: 1, // 1분 단위로 정밀 설정
                    onDateTimeChanged: (DateTime newTime) {
                      tempStart = newTime;
                    },
                  ),
                ),
                
                const Divider(height: 1),
                
                // 2. 종료 시간(기상) 픽커 영역
                const Padding(
                  padding: EdgeInsets.only(top: 16.0, bottom: 8.0),
                  child: Text('☀️ 종료 시간 설정', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Colors.black87)),
                ),
                Expanded(
                  child: CupertinoDatePicker(
                    mode: CupertinoDatePickerMode.time,
                    use24hFormat: true,
                    initialDateTime: tempEnd,
                    minuteInterval: 1, // 1분 단위로 정밀 설정
                    onDateTimeChanged: (DateTime newTime) {
                      tempEnd = newTime;
                    },
                  ),
                ),
                const SizedBox(height: 10),
              ],
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final Color backgroundColor = _isCurrentlyNightTime() 
        ? const Color(0xFFFFF5E1) 
        : Colors.white;

    return AnimatedContainer(
      duration: const Duration(seconds: 1),
      width: 320, 
      padding: const EdgeInsets.all(24.0),
      decoration: BoxDecoration(
        color: backgroundColor,
        borderRadius: BorderRadius.circular(24.0),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 15,
            spreadRadius: 2,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  Icon(Icons.dark_mode, color: Colors.grey.shade800, size: 28),
                  const SizedBox(width: 8),
                  Text(
                    "NIGHT MODE",
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.2,
                      color: Colors.grey.shade800,
                    ),
                  ),
                ],
              ),
              GestureDetector(
                onTap: () {
                  setState(() {
                    isNightModeOn = !isNightModeOn;
                  });
                },
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 60,
                  height: 30,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(15.0),
                    color: isNightModeOn ? Colors.grey.shade800 : Colors.grey.shade300,
                  ),
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      Positioned(
                        left: isNightModeOn ? 8 : null,
                        right: isNightModeOn ? null : 8,
                        child: Text(
                          isNightModeOn ? "ON" : "OFF",
                          style: TextStyle(
                            color: isNightModeOn ? Colors.white : Colors.grey.shade600,
                            fontWeight: FontWeight.bold,
                            fontSize: 12,
                          ),
                        ),
                      ),
                      AnimatedPositioned(
                        duration: const Duration(milliseconds: 200),
                        curve: Curves.easeInOut,
                        left: isNightModeOn ? 32 : 2,
                        child: Container(
                          width: 26,
                          height: 26,
                          decoration: const BoxDecoration(
                            shape: BoxShape.circle,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          
          const SizedBox(height: 30),
          
          IgnorePointer(
            ignoring: !isNightModeOn, 
            child: Opacity(
              opacity: isNightModeOn ? 1.0 : 0.4, 
              child: TimePicker(
                initTime: _startTime,
                endTime: _endTime,
                height: 220,
                width: 220,
                onSelectionChange: (PickedTime start, PickedTime end, bool? isResolvable) {
                  setState(() {
                    _startTime = start;
                    _endTime = end;
                  });
                },
                onSelectionEnd: (PickedTime start, PickedTime end, bool? isResolvable) {
                  setState(() {
                    _startTime = start;
                    _endTime = end;
                  });
                },
                decoration: TimePickerDecoration(
                  baseColor: Colors.grey.shade200, 
                  sweepDecoration: TimePickerSweepDecoration(
                    pickerStrokeWidth: 16,
                    pickerColor: Colors.grey.shade800, 
                    showConnector: true,
                  ),
                  initHandlerDecoration: TimePickerHandlerDecoration(
                    color: Colors.grey.shade800,
                    shape: BoxShape.circle,
                    radius: 14,
                    icon: const Icon(Icons.bedtime, size: 16, color: Colors.white),
                  ),
                  endHandlerDecoration: TimePickerHandlerDecoration(
                    color: Colors.grey.shade800,
                    shape: BoxShape.circle,
                    radius: 14,
                    icon: const Icon(Icons.wb_sunny, size: 16, color: Colors.white),
                  ),
                  clockNumberDecoration: TimePickerClockNumberDecoration(
                    defaultTextColor: Colors.grey.shade600, // 색상을 살짝 더 진하게
                    defaultFontSize: 18, // 💡 수정사항: 12 -> 18로 크기 대폭 증가
                    showNumberIndicators: true,
                    clockTimeFormat: ClockTimeFormat.twentyFourHours,
                  ),
                ),
              ),
            ),
          ),
          
          const SizedBox(height: 20),
          
          // 💡 수정사항: 텍스트를 감싸서 터치 가능하게 만들고, 터치 피드백을 위해 투명한 배경 박스를 주었습니다.
          GestureDetector(
            onTap: isNightModeOn ? () => _showManualTimePicker(context) : null,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              decoration: BoxDecoration(
                color: isNightModeOn ? Colors.grey.shade100 : Colors.transparent, // 터치할 수 있는 버튼 느낌
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                '${_formatTime(_startTime)} ~ ${_formatTime(_endTime)}',
                style: TextStyle(
                  fontSize: 26, // 텍스트 크기도 24 -> 26으로 살짝 키움
                  fontWeight: FontWeight.bold,
                  color: isNightModeOn ? Colors.grey.shade800 : Colors.grey.shade400,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}