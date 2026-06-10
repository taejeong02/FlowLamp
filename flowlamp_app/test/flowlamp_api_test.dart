import 'package:flowlamp_app/services/flowlamp_api.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('getStudyRecords sends date range and parses scores', () async {
    final client = MockClient((request) async {
      expect(request.url.path, '/study-records');
      expect(request.url.queryParameters['start_date'], '2026-05-01');
      expect(request.url.queryParameters['end_date'], '2026-05-03');

      return http.Response(
        '''
        {
          "start_date": "2026-05-01",
          "end_date": "2026-05-03",
          "count": 1,
          "records": [
            {
              "study_date": "2026-05-02",
              "posture_score": 38,
              "focus_score": 42,
              "total_score": 80
            }
          ]
        }
        ''',
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      );
    });
    final api = FlowLampApi(baseUrl: 'http://rpi.local:8000', client: client);

    final records = await api.getStudyRecords(
      startDate: DateTime(2026, 5, 1),
      endDate: DateTime(2026, 5, 3),
    );

    expect(records, hasLength(1));
    expect(records.single.studyDate, DateTime(2026, 5, 2));
    expect(records.single.postureScore, 38);
    expect(records.single.focusScore, 42);
    expect(records.single.totalScore, 80);
  });
}
