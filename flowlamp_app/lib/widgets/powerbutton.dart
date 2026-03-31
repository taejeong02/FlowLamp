import 'package:flutter/material.dart';

class PowerButton extends StatelessWidget {
  final bool isOn;
  final VoidCallback onTap;

  const PowerButton({
    super.key,
    required this.isOn,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: SizedBox(
        width: 300,
        height: 300,
        child: Image.asset(
          isOn ? 'assets/Lamp_On.png' : 'assets/Lamp_Off.png',
          fit: BoxFit.contain,
        ),
      ),
    );
  }
}