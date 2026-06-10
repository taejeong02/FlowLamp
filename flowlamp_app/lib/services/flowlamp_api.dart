import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/study_record.dart';

class FlowLampApi {
  static const String _defaultBaseUrl = 'http://172.20.10.6:8000';
  static const Duration _requestTimeout = Duration(seconds: 5);

  FlowLampApi({
    String baseUrl = const String.fromEnvironment(
      'FLOWLAMP_API_BASE',
      defaultValue: _defaultBaseUrl,
    ),
    http.Client? client,
  }) : baseUrl = baseUrl.endsWith('/')
           ? baseUrl.substring(0, baseUrl.length - 1)
           : baseUrl,
       _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

  Future<Map<String, dynamic>> setPower(bool isOn) {
    return _postQuery('/power', {'status': isOn ? 'on' : 'off'});
  }

  Future<Map<String, dynamic>> setColor({
    required int red,
    required int green,
    required int blue,
  }) {
    return _postJson('/color', {'r': red, 'g': green, 'b': blue});
  }

  Future<Map<String, dynamic>> setBrightness(int value) {
    return _postJson('/brightness', {'value': value});
  }

  Future<Map<String, dynamic>> notifyTimerDone() {
    return _postQuery('/timer/done');
  }

  Future<Map<String, dynamic>> setMotorVelocity({
    required int motorId,
    required int velocity,
  }) {
    return _postJson('/motors/$motorId/velocity', {'velocity': velocity});
  }

  Future<Map<String, dynamic>> getNightSchedule() async {
    final response = await _client
        .get(Uri.parse('$baseUrl/night_mode/schedule'))
        .timeout(_requestTimeout);
    return _decodeResponse(response);
  }

  Future<Map<String, dynamic>> setNightSchedule({
    required bool isOn,
    required String startTime,
    required String endTime,
  }) {
    return _postJson('/night_mode/schedule', {
      'is_on': isOn,
      'start_time': startTime,
      'end_time': endTime,
    });
  }

  Future<Map<String, dynamic>> setNightMode(bool active) {
    return getNightSchedule().then((schedule) {
      return setNightSchedule(
        isOn: active,
        startTime: schedule['start_time']?.toString() ?? '23:00',
        endTime: schedule['end_time']?.toString() ?? '06:00',
      );
    });
  }

  Future<Map<String, dynamic>> getStatus() async {
    final response = await _client
        .get(Uri.parse('$baseUrl/status'))
        .timeout(_requestTimeout);
    return _decodeResponse(response);
  }

  Future<List<StudyRecord>> getStudyRecords({
    required DateTime startDate,
    required DateTime endDate,
  }) async {
    final uri = Uri.parse('$baseUrl/study-records').replace(
      queryParameters: {
        'start_date': _dateOnly(startDate),
        'end_date': _dateOnly(endDate),
      },
    );
    final response = await _client.get(uri).timeout(_requestTimeout);
    final body = _decodeResponse(response);
    final records = body['records'];

    if (records is! List) {
      throw const FormatException('Expected records to be a JSON array.');
    }

    return records.map((record) {
      if (record is! Map) {
        throw const FormatException(
          'Expected each record to be a JSON object.',
        );
      }
      return StudyRecord.fromJson(Map<String, dynamic>.from(record));
    }).toList();
  }

  String _dateOnly(DateTime value) {
    final month = value.month.toString().padLeft(2, '0');
    final day = value.day.toString().padLeft(2, '0');
    return '${value.year}-$month-$day';
  }

  Future<Map<String, dynamic>> _postQuery(
    String path, [
    Map<String, String> queryParameters = const {},
  ]) async {
    final uri = Uri.parse(
      '$baseUrl$path',
    ).replace(queryParameters: queryParameters);
    final response = await _client.post(uri).timeout(_requestTimeout);
    return _decodeResponse(response);
  }

  Future<Map<String, dynamic>> _postJson(
    String path,
    Map<String, dynamic> body,
  ) async {
    final response = await _client
        .post(
          Uri.parse('$baseUrl$path'),
          headers: const {'Content-Type': 'application/json'},
          body: jsonEncode(body),
        )
        .timeout(_requestTimeout);
    return _decodeResponse(response);
  }

  Map<String, dynamic> _decodeResponse(http.Response response) {
    final Object? body = response.bodyBytes.isEmpty
        ? null
        : jsonDecode(utf8.decode(response.bodyBytes));

    if (response.statusCode >= 200 && response.statusCode < 300) {
      if (body is Map<String, dynamic>) {
        return body;
      }
      if (body is Map) {
        return Map<String, dynamic>.from(body);
      }
      throw FlowLampApiException(
        response.statusCode,
        'Expected a JSON object but received ${body.runtimeType}',
      );
    }

    throw FlowLampApiException(response.statusCode, _errorMessage(body));
  }

  String _errorMessage(Object? body) {
    if (body is Map && body['detail'] != null) {
      return body['detail'].toString();
    }
    return body?.toString() ?? 'Empty response';
  }
}

class FlowLampApiException implements Exception {
  const FlowLampApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'FlowLampApiException($statusCode): $message';
}
