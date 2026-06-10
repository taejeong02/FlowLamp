import 'dart:async';

import 'package:flutter/material.dart';

import '../services/flowlamp_api.dart';

class Tab4Manual extends StatefulWidget {
  Tab4Manual({super.key, FlowLampApi? api}) : api = api ?? FlowLampApi();

  final FlowLampApi api;

  @override
  State<Tab4Manual> createState() => _Tab4ManualState();
}

class _Tab4ManualState extends State<Tab4Manual> with WidgetsBindingObserver {
  static const List<int> _motorIds = [1, 4];
  static const int _motorSpeed = 20;

  Future<void> _motorCommandQueue = Future<void>.value();
  int? _activePointer;
  int? _activeMotor;
  String _statusMessage = '1번과 4번 모터를 버튼을 누르는 동안 수동 제어합니다.';
  bool _statusIsError = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) {
      _stopActiveMotor();
    }
  }

  bool _startMotor(PointerDownEvent event, int motorNumber, int direction) {
    if (_activePointer != null) {
      return false;
    }

    _activePointer = event.pointer;
    _activeMotor = motorNumber;
    _queueMotorVelocity(motorNumber, direction * _motorSpeed);
    return true;
  }

  void _stopMotor(PointerEvent event, int motorNumber) {
    if (_activePointer != event.pointer || _activeMotor != motorNumber) {
      return;
    }
    _stopActiveMotor();
  }

  void _stopActiveMotor() {
    final motorNumber = _activeMotor;
    _activePointer = null;
    _activeMotor = null;

    if (motorNumber != null) {
      _queueMotorVelocity(motorNumber, 0);
    }
  }

  void _queueMotorVelocity(int motorNumber, int velocity) {
    _motorCommandQueue = _motorCommandQueue.then<void>((_) async {
      try {
        await widget.api.setMotorVelocity(
          motorId: motorNumber,
          velocity: velocity,
        );
        if (!mounted) {
          return;
        }
        setState(() {
          _statusMessage = velocity == 0
              ? '$motorNumber번 모터 정지'
              : '$motorNumber번 모터 속도 $velocity 전송';
          _statusIsError = false;
        });
      } catch (error) {
        debugPrint(
          'FlowLamp motor $motorNumber velocity $velocity error: $error',
        );
        if (!mounted) {
          return;
        }
        setState(() {
          _statusMessage = '$motorNumber번 모터 제어 실패: $error';
          _statusIsError = true;
        });
      }
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _stopActiveMotor();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        _buildStatusCard(),
        const SizedBox(height: 16),
        ..._motorIds.map(_buildMotorControlPanel),
        const SizedBox(height: 20),
      ],
    );
  }

  Widget _buildStatusCard() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: _statusIsError ? Colors.red.shade50 : Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: _statusIsError ? Colors.red.shade200 : Colors.amber.shade200,
        ),
      ),
      child: Row(
        children: [
          Icon(
            _statusIsError ? Icons.error_outline : Icons.info_outline,
            color: _statusIsError ? Colors.red : Colors.amber.shade700,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              _statusMessage,
              style: TextStyle(
                color: _statusIsError ? Colors.red.shade700 : Colors.black87,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMotorControlPanel(int motorNumber) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          _HoldMotorButton(
            key: ValueKey('motor-$motorNumber-left'),
            icon: Icons.chevron_left_rounded,
            semanticLabel: '$motorNumber번 모터 왼쪽 이동',
            onPointerDown: (event) {
              return _startMotor(event, motorNumber, -1);
            },
            onPointerUp: (event) => _stopMotor(event, motorNumber),
            onPointerCancel: (event) => _stopMotor(event, motorNumber),
          ),
          Text(
            '$motorNumber번 모터',
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
          ),
          _HoldMotorButton(
            key: ValueKey('motor-$motorNumber-right'),
            icon: Icons.chevron_right_rounded,
            semanticLabel: '$motorNumber번 모터 오른쪽 이동',
            onPointerDown: (event) {
              return _startMotor(event, motorNumber, 1);
            },
            onPointerUp: (event) => _stopMotor(event, motorNumber),
            onPointerCancel: (event) => _stopMotor(event, motorNumber),
          ),
        ],
      ),
    );
  }
}

class _HoldMotorButton extends StatefulWidget {
  const _HoldMotorButton({
    required super.key,
    required this.icon,
    required this.semanticLabel,
    required this.onPointerDown,
    required this.onPointerUp,
    required this.onPointerCancel,
  });

  final IconData icon;
  final String semanticLabel;
  final bool Function(PointerDownEvent event) onPointerDown;
  final void Function(PointerUpEvent event) onPointerUp;
  final void Function(PointerCancelEvent event) onPointerCancel;

  @override
  State<_HoldMotorButton> createState() => _HoldMotorButtonState();
}

class _HoldMotorButtonState extends State<_HoldMotorButton> {
  bool _isPressed = false;

  void _handlePointerDown(PointerDownEvent event) {
    final accepted = widget.onPointerDown(event);
    if (accepted) {
      setState(() => _isPressed = true);
    }
  }

  void _handlePointerUp(PointerUpEvent event) {
    if (!_isPressed) {
      return;
    }
    widget.onPointerUp(event);
    setState(() => _isPressed = false);
  }

  void _handlePointerCancel(PointerCancelEvent event) {
    if (!_isPressed) {
      return;
    }
    widget.onPointerCancel(event);
    setState(() => _isPressed = false);
  }

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: widget.semanticLabel,
      child: Listener(
        behavior: HitTestBehavior.opaque,
        onPointerDown: _handlePointerDown,
        onPointerUp: _handlePointerUp,
        onPointerCancel: _handlePointerCancel,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 80),
          width: 48,
          height: 48,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: _isPressed
                ? Colors.amber.withValues(alpha: 0.2)
                : Colors.transparent,
          ),
          child: Icon(widget.icon, size: 32, color: Colors.amber.shade700),
        ),
      ),
    );
  }
}
