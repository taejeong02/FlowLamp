import 'package:flutter/material.dart';
import '../widgets/focus_timer.dart'; 
import '../widgets/night_mode_card.dart';

class AlarmRoutineTab extends StatelessWidget {
  const AlarmRoutineTab({super.key});

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Column(
        children: [
          Expanded(
            flex: 45,
            child: Center(
              child: FittedBox(
                fit: BoxFit.scaleDown,
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 20.0),
                  child: const FocusTimerSection(),
                ),
              ),
            ),
          ),
          Expanded(
            flex: 55,
            child: Center(
              child: FittedBox(
                fit: BoxFit.scaleDown,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 10.0),
                  child: const NightModeCard(),
                ),
              ),
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }
}