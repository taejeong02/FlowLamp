import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:flowlamp_app/main.dart';
import 'package:flowlamp_app/services/flowlamp_api.dart';
import 'package:flowlamp_app/widgets/powerbutton.dart';

class FakeFlowLampApi extends FlowLampApi {
  FakeFlowLampApi() : super(baseUrl: 'http://fake.local');

  bool isOn = false;
  List<int> color = [255, 255, 255];

  @override
  Future<Map<String, dynamic>> getStatus() async {
    return {'is_on': isOn, 'color': color};
  }

  @override
  Future<Map<String, dynamic>> setPower(bool nextValue) async {
    isOn = nextValue;
    return {'is_on': isOn};
  }

  @override
  Future<Map<String, dynamic>> setColor({
    required int red,
    required int green,
    required int blue,
  }) async {
    color = [red, green, blue];
    return {'color': color, 'is_on': isOn};
  }
}

void main() {
  testWidgets('power button sends a power toggle request', (tester) async {
    final api = FakeFlowLampApi();

    await tester.pumpWidget(
      MaterialApp(
        home: MyHomePage(title: 'Flow_Lamp', api: api),
      ),
    );
    await tester.pump();

    expect(api.isOn, isFalse);

    await tester.tap(find.byType(PowerButton));
    await tester.pump();

    expect(api.isOn, isTrue);
  });

  testWidgets('color slider sends a color request when drag ends', (
    tester,
  ) async {
    final api = FakeFlowLampApi();

    await tester.pumpWidget(
      MaterialApp(
        home: MyHomePage(title: 'Flow_Lamp', api: api),
      ),
    );
    await tester.pump();

    await tester.drag(find.byType(Slider).first, const Offset(400, 0));
    await tester.pump();

    expect(api.color, isNot([255, 255, 255]));
  });
}
