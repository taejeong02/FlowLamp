import 'package:flutter/material.dart';

class ColorSlider extends StatelessWidget {
  final double value;
  final ValueChanged<double> onChanged;

  const ColorSlider({super.key, required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const Align(alignment: Alignment.centerLeft, child: Text("LED 색상 (RGB)")),
        Slider(
          value: value,
          activeColor: Colors.purpleAccent,
          onChanged: onChanged,
        ),
      ],
    );
  }
}