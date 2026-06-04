import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/cupertino.dart';
import 'package:progressive_time_picker/progressive_time_picker.dart';

import '../services/flowlamp_api.dart';

class NightModeCard extends StatefulWidget {
  const NightModeCard({super.key});

  @override
  State<NightModeCard> createState() => _NightModeCardState();
}

class _NightModeCardState extends State<NightModeCard> {
  final FlowLampApi _api = FlowLampApi();
  int _scheduleRequestId = 0;

  bool isNightModeOn = true;
  Timer? _minuteTimer;

  PickedTime _startTime = PickedTime(h: 23, m: 0);
  PickedTime _endTime = PickedTime(h: 6, m: 0);

  @override
  void initState() {
    super.initState();
    _loadNightSchedule();
    _minuteTimer = Timer.periodic(const Duration(minutes: 1), (timer) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _minuteTimer?.cancel();
    super.dispose();
  }

  Future<void> _loadNightSchedule() async {
    try {
      final schedule = await _api.getNightSchedule();
      if (!mounted) return;
      _applyNightSchedule(schedule);
    } catch (error) {
      debugPrint('FlowLamp night schedule load error: $error');
    }
  }

  Future<void> _saveNightSchedule() async {
    final requestId = ++_scheduleRequestId;
    try {
      final schedule = await _api.setNightSchedule(
        isOn: isNightModeOn,
        startTime: _formatTime(_startTime),
        endTime: _formatTime(_endTime),
      );
      if (!mounted || requestId != _scheduleRequestId) return;
      _applyNightSchedule(schedule);
    } catch (error) {
      debugPrint('FlowLamp night schedule save error: $error');
    }
  }

  void _applyNightSchedule(Map<String, dynamic> schedule) {
    final startTime = _parsePickedTime(schedule['start_time']);
    final endTime = _parsePickedTime(schedule['end_time']);
    final isOn = schedule['is_on'];

    setState(() {
      if (isOn is bool) {
        isNightModeOn = isOn;
      }
      if (startTime != null) {
        _startTime = startTime;
      }
      if (endTime != null) {
        _endTime = endTime;
      }
    });
  }

  PickedTime? _parsePickedTime(Object? value) {
    if (value is! String) return null;

    final parts = value.split(':');
    if (parts.length != 2) return null;

    final hour = int.tryParse(parts[0]);
    final minute = int.tryParse(parts[1]);
    if (hour == null || minute == null) return null;
    if (hour < 0 || hour > 23 || minute < 0 || minute > 59) return null;

    return PickedTime(h: hour, m: minute);
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
                  const Text(
                    "NIGHT MODE",
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.2,
                    ),
                  ),
                ],
              ),
              Switch(
                value: isNightModeOn,
                onChanged: (v) {
                  setState(() => isNightModeOn = v);
                  _saveNightSchedule();
                },
              ),
            ],
          ),
          const SizedBox(height: 20),
          // 💡 필수 인자들을 모두 채워 넣은 TimePicker
          TimePicker(
            initTime: _startTime,
            endTime: _endTime,
            height: 200,
            width: 200,
            onSelectionChange: (start, end, res) => setState(() {
              _startTime = start;
              _endTime = end;
            }),
            onSelectionEnd: (start, end, res) {
              setState(() {
                _startTime = start;
                _endTime = end;
              });
              _saveNightSchedule();
            },
            decoration: TimePickerDecoration(
              baseColor: Colors.grey.shade200,
              sweepDecoration: TimePickerSweepDecoration(
                pickerColor: Colors.grey.shade800,
                pickerStrokeWidth: 12,
              ),
              initHandlerDecoration: TimePickerHandlerDecoration(
                color: Colors.grey.shade800,
                shape: BoxShape.circle,
                radius: 12,
              ),
              endHandlerDecoration: TimePickerHandlerDecoration(
                color: Colors.grey.shade800,
                shape: BoxShape.circle,
                radius: 12,
              ),
            ),
          ),
          const SizedBox(height: 20),
          Text(
            '${_formatTime(_startTime)} ~ ${_formatTime(_endTime)}',
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}
