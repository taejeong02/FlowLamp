import 'package:flutter/material.dart';

class ColorSlider extends StatelessWidget {
  final double value;
  final ValueChanged<double> onChanged;

  const ColorSlider({super.key, required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Container(
        width: double.infinity,
        child: Stack(
          alignment: Alignment.center,
          children: [
            Container(
              height: 50,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(50),
                gradient: const LinearGradient(
                  colors: [
                    Colors.red,
                    Colors.orange,
                    Colors.yellow,
                    Colors.green,
                    Colors.cyan,
                    Colors.blue,
                    Colors.purple,
                  ],
                ),
              ),
            ),

            SliderTheme(
              data: SliderTheme.of(context).copyWith(
                trackHeight: 0,
                thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 20),
                overlayShape: const RoundSliderOverlayShape(overlayRadius: 30),
              ),
              child: Slider(
                value: value,
                min: 0,
                max: 100, //
                onChanged: onChanged,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
