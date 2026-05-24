import 'package:flutter/material.dart';
import 'main_screen.dart';

void main() {
  runApp(const FlowLampApp());
}

class FlowLampApp extends StatelessWidget {
  const FlowLampApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flow Lamp',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.amber),
        useMaterial3: true,
      ),
      home: const MainScreen(),
    );
  }
}