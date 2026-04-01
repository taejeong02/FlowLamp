import 'package:flutter/material.dart';

class AlarmCard extends StatelessWidget {
  const AlarmCard({super.key});

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 20).copyWith(top: 30),
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 50),
        decoration: BoxDecoration(
          color: const Color(0xFFF2F2F2),
          borderRadius: BorderRadius.circular(28),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.12),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: const [
            Icon(Icons.access_alarm, size: 50),
            SizedBox(height: 10),
            Text(
              "알람 및 루틴",
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: Colors.black87,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
