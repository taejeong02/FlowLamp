import 'package:flutter/material.dart';

class PowerButton extends StatelessWidget {
  final bool isOn;
  final bool isLoading;
  final VoidCallback onTap;

  const PowerButton({
    super.key,
    required this.isOn,
    required this.onTap,
    this.isLoading = false,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: isLoading ? null : onTap,
      borderRadius: BorderRadius.circular(24),
      child: SizedBox(
        width: 300,
        height: 300,
        child: Stack(
          alignment: Alignment.center,
          children: [
            AnimatedOpacity(
              duration: const Duration(milliseconds: 180),
              opacity: isLoading ? 0.55 : 1,
              child: Image.asset(
                isOn ? 'assets/Lamp_On.png' : 'assets/Lamp_Off.png',
                fit: BoxFit.contain,
              ),
            ),
            if (isLoading)
              const SizedBox(
                width: 48,
                height: 48,
                child: CircularProgressIndicator(strokeWidth: 4),
              ),
          ],
        ),
      ),
    );
  }
}
