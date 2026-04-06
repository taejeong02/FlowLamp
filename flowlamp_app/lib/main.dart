import 'package:flutter/material.dart';
import 'widgets/colorslider.dart';
import 'widgets/powerbutton.dart';
import 'widgets/brightslider.dart';
import 'widgets/sleepbutton.dart';
import 'widgets/alarmbutton.dart';
import 'widgets/anglebutton.dart';
import 'alarm.dart';

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Demo',
      theme: ThemeData(
        // This is the theme of your application.
        //
        // TRY THIS: Try running your application with "flutter run". You'll see
        // the application has a purple toolbar. Then, without quitting the app,
        // try changing the seedColor in the colorScheme below to Colors.green
        // and then invoke "hot reload" (save your changes or press the "hot
        // reload" button in a Flutter-supported IDE, or press "r" if you used
        // the command line to start the app).
        //
        // Notice that the counter didn't reset back to zero; the application
        // state is not lost during the reload. To reset the state, use hot
        // restart instead.
        //
        // This works for code too, not just values: Most code changes can be
        // tested with just a hot reload.
        colorScheme: .fromSeed(seedColor: Colors.deepPurple),
      ),
      home: const MyHomePage(title: 'Flow_Lamp'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});

  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  bool isOn = false;
  double sliderValue = 0.5;
  double brightness = 50;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Flow Lamp")),
      body: Container(
        width: double.infinity, // 가로 전체 차지
        padding: const EdgeInsets.only(top: 60), // 위쪽 위치 조절
        child: Column(
          mainAxisAlignment: MainAxisAlignment.start, // 위쪽 정렬
          crossAxisAlignment: CrossAxisAlignment.center, // 가로 중앙
          children: [
            PowerButton(
              isOn: isOn,
              onTap: () {
                setState(() {
                  isOn = !isOn;
                });
              },
            ),
            ColorSlider(
              value: sliderValue,
              onChanged: (value) {
                setState(() {
                  sliderValue = value;
                });
              },
            ),
            BrightnessSlider(
              value: brightness,
              onChanged: (value) {
                setState(() {
                  brightness = value;
                });
              },
            ),
            SleepingButton(),
            Row(
              children: [
                Expanded(
                  child: InkWell(
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (context) => AlarmScreen()),
                      );
                    },
                    child: const AlarmCard(),
                  ),
                ),

                const SizedBox(width: 10),

                Expanded(
                  child: InkWell(
                    onTap: () {
                      Navigator.push(
                        context,
                        MaterialPageRoute(builder: (context) => AlarmScreen()), //이거 나중에 각도 페이지 넣기
                      );
                    },
                    child: const AngleCard(),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
