import 'package:flutter/material.dart';

class BrightnessSlider extends StatelessWidget {
  final double value;
  final ValueChanged<double> onChanged;

  const BrightnessSlider({super.key, required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Icon(Icons.brightness_medium),
            Text("${value.toInt()}%"),
          ],
        ),
        Slider(
          value: value,
          min: 0,
          max: 100,
          activeColor: Colors.amber,
          onChanged: onChanged,
        ),
      ],
    );
  }
}