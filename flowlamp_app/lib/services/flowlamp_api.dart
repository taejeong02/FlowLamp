import 'dart:convert';

import 'package:http/http.dart' as http;

class FlowLampApi {
  static const String _defaultBaseUrl = 'http://localhost:8000';

  FlowLampApi({
    String baseUrl = const String.fromEnvironment(
      'FLOWLAMP_API_BASE',
      defaultValue: _defaultBaseUrl,
    ),
    http.Client? client,
  })  : baseUrl = baseUrl.endsWith('/')
            ? baseUrl.substring(0, baseUrl.length - 1)
            : baseUrl,
        _client = client ?? http.Client();

  final String baseUrl;
  final http.Client _client;

  Future<Map<String, dynamic>> setPower(bool isOn) {
    return _postQuery(
      '/power',
      {'status': isOn ? 'on' : 'off'},
    );
  }

  Future<Map<String, dynamic>> setNightMode(bool active) {
    return _postQuery(
      '/mode/night',
      {'active': active.toString()},
    );
  }

  Future<Map<String, dynamic>> getStatus() async {
    final response = await _client.get(Uri.parse('$baseUrl/status'));
    return _decodeResponse(response);
  }

  Future<Map<String, dynamic>> _postQuery(
    String path,
    Map<String, String> queryParameters,
  ) async {
    final uri = Uri.parse('$baseUrl$path').replace(
      queryParameters: queryParameters,
    );
    final response = await _client.post(uri);
    return _decodeResponse(response);
  }

  Map<String, dynamic> _decodeResponse(http.Response response) {
    final body = jsonDecode(utf8.decode(response.bodyBytes));
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return body as Map<String, dynamic>;
    }

    throw FlowLampApiException(response.statusCode, body.toString());
  }
}

class FlowLampApiException implements Exception {
  const FlowLampApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'FlowLampApiException($statusCode): $message';
}
