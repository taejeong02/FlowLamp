class StudyRecord {
  const StudyRecord({
    required this.studyDate,
    required this.postureScore,
    required this.focusScore,
    required this.totalScore,
  });

  factory StudyRecord.fromJson(Map<String, dynamic> json) {
    return StudyRecord(
      studyDate: DateTime.parse(json['study_date'] as String),
      postureScore: _score(json['posture_score']),
      focusScore: _score(json['focus_score']),
      totalScore: _score(json['total_score']),
    );
  }

  final DateTime studyDate;
  final double postureScore;
  final double focusScore;
  final double totalScore;

  static double _score(Object? value) {
    return value is num ? value.toDouble() : 0;
  }
}
