import 'package:flutter/material.dart';

class PowerButton extends StatelessWidget {
  final bool isOn;
  final VoidCallback onTap;

  const PowerButton({super.key, required this.isOn, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 300),
        width: 120,
        height: 120,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: isOn ? Colors.amber : Colors.grey.shade300,
          boxShadow: [
            BoxShadow(
              color: (isOn ? Colors.amber : Colors.black).withOpacity(0.3),
              blurRadius: 15,
              offset: const Offset(0, 5),
            ),
          ],
        ),
        child: Icon(
          Icons.power_settings_new,
          size: 60,
          color: isOn ? Colors.white : Colors.grey.shade600,
        ),
      ),
    );
  }
}