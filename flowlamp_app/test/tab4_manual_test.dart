import 'dart:convert';

import 'package:flowlamp_app/screens/tab4_manual.dart';
import 'package:flowlamp_app/services/flowlamp_api.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  testWidgets('motor moves while held and stops on release', (tester) async {
    final requests = <http.Request>[];
    final client = MockClient((request) async {
      requests.add(request);
      return http.Response('{"status":"success"}', 200);
    });
    final api = FlowLampApi(baseUrl: 'http://rpi.local:8000', client: client);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: Tab4Manual(api: api)),
      ),
    );

    final button = find.byKey(const ValueKey('motor-1-left'));
    final gesture = await tester.startGesture(tester.getCenter(button));
    await tester.pumpAndSettle();

    expect(requests, hasLength(1));
    expect(requests.single.url.path, '/motor/1/velocity');
    expect(jsonDecode(requests.single.body), {'value': -20});

    await tester.pump(const Duration(milliseconds: 500));
    expect(requests, hasLength(1));

    await gesture.up();
    await tester.pumpAndSettle();

    expect(requests, hasLength(2));
    expect(requests.last.url.path, '/motor/1/velocity');
    expect(jsonDecode(requests.last.body), {'value': 0});
  });
}
