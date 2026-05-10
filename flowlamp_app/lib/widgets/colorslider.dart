import 'package:flutter/material.dart';

class ColorSlider extends StatelessWidget {
  final double value;
  final ValueChanged<double> onChanged;
  final ValueChanged<double>? onChangeEnd;
  final bool isEnabled;

  const ColorSlider({
    super.key,
    required this.value,
    required this.onChanged,
    this.onChangeEnd,
    this.isEnabled = true,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 20),
      child: Opacity(
        opacity: isEnabled ? 1 : 0.55,
        child: SizedBox(
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
                  thumbShape: const RoundSliderThumbShape(
                    enabledThumbRadius: 20,
                  ),
                  overlayShape: const RoundSliderOverlayShape(
                    overlayRadius: 30,
                  ),
                ),
                child: Slider(
                  value: value,
                  min: 0,
                  max: 100,
                  onChanged: isEnabled ? onChanged : null,
                  onChangeEnd: isEnabled ? onChangeEnd : null,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
