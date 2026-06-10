import 'dart:math';

import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/study_record.dart';
import '../services/flowlamp_api.dart';

class Tab3Data extends StatefulWidget {
  Tab3Data({super.key, FlowLampApi? api}) : api = api ?? FlowLampApi();

  final FlowLampApi api;

  @override
  State<Tab3Data> createState() => _Tab3DataState();
}

class _Tab3DataState extends State<Tab3Data> {
  static const List<String> _categories = ['집중 점수', '자세 점수', '종합 점수'];

  int _selectedCategoryIndex = 0;
  int _requestId = 0;
  late DateTimeRange _selectedRange;
  List<StudyRecord> _records = const [];
  bool _isLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final today = DateUtils.dateOnly(DateTime.now());
    _selectedRange = DateTimeRange(
      start: today.subtract(const Duration(days: 29)),
      end: today,
    );
    _loadRecords();
  }

  Future<void> _loadRecords() async {
    final requestId = ++_requestId;
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final records = await widget.api.getStudyRecords(
        startDate: _selectedRange.start,
        endDate: _selectedRange.end,
      );
      if (!mounted || requestId != _requestId) {
        return;
      }
      setState(() {
        _records = records;
        _isLoading = false;
      });
    } catch (error) {
      if (!mounted || requestId != _requestId) {
        return;
      }
      setState(() {
        _records = const [];
        _isLoading = false;
        _error = error.toString();
      });
    }
  }

  Future<void> _selectDateRange() async {
    final today = DateUtils.dateOnly(DateTime.now());
    final range = await showDateRangePicker(
      context: context,
      firstDate: DateTime(2020),
      lastDate: today,
      initialDateRange: _selectedRange,
      initialEntryMode: DatePickerEntryMode.calendarOnly,
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: const ColorScheme.light(primary: Colors.amber),
          ),
          child: child!,
        );
      },
    );

    if (range == null || !mounted) {
      return;
    }
    setState(() => _selectedRange = range);
    await _loadRecords();
  }

  double _scoreFor(StudyRecord record) {
    return switch (_selectedCategoryIndex) {
      0 => record.focusScore,
      1 => record.postureScore,
      _ => record.totalScore,
    };
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 8, 12),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Colors.amber),
                ),
                icon: const Icon(Icons.calendar_month, color: Colors.amber),
                label: Text(
                  '${DateFormat('yyyy.MM.dd').format(_selectedRange.start)}'
                  ' ~ ${DateFormat('yyyy.MM.dd').format(_selectedRange.end)}',
                ),
                onPressed: _selectDateRange,
              ),
              IconButton(
                tooltip: '새로고침',
                onPressed: _isLoading ? null : _loadRecords,
                icon: const Icon(Icons.refresh),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(
            children: List.generate(_categories.length, (index) {
              final selected = _selectedCategoryIndex == index;
              return Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                  child: Material(
                    color: selected ? Colors.amber : Colors.grey.shade200,
                    borderRadius: BorderRadius.circular(10),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(10),
                      onTap: () {
                        setState(() => _selectedCategoryIndex = index);
                      },
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        child: Text(
                          _categories[index],
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            color: selected ? Colors.white : Colors.black,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              );
            }),
          ),
        ),
        Expanded(child: _buildContent()),
      ],
    );
  }

  Widget _buildContent() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: Colors.amber),
      );
    }
    if (_error != null) {
      return _MessageState(
        icon: Icons.cloud_off,
        title: '데이터를 불러오지 못했습니다.',
        detail: _error!,
        actionLabel: '다시 시도',
        onAction: _loadRecords,
      );
    }
    if (_records.isEmpty) {
      return const _MessageState(
        icon: Icons.bar_chart_outlined,
        title: '선택한 기간에 학습 데이터가 없습니다.',
        detail: '다른 날짜 범위를 선택해 주세요.',
      );
    }

    final scores = _records.map(_scoreFor).toList();
    final maxScore = scores.reduce(max);
    final minScore = scores.reduce(min);
    final average = scores.reduce((a, b) => a + b) / scores.length;

    return Column(
      children: [
        Expanded(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 40, 32, 20),
            child: _buildChart(scores),
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildSummary('최고', maxScore),
              _buildSummary('최저', minScore),
              _buildSummary('평균', average),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildChart(List<double> scores) {
    final chartMax = _selectedCategoryIndex == 2 ? 100.0 : 50.0;
    final bottomInterval = max(1, (_records.length / 5).ceil()).toDouble();

    return LineChart(
      LineChartData(
        minY: 0,
        maxY: chartMax,
        gridData: const FlGridData(show: false),
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (spots) {
              return spots.map((spot) {
                return LineTooltipItem(
                  '${spot.y.toStringAsFixed(1)}점',
                  const TextStyle(color: Colors.white),
                );
              }).toList();
            },
          ),
        ),
        titlesData: FlTitlesData(
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: chartMax / 5,
              reservedSize: 32,
              getTitlesWidget: (value, meta) {
                if (value == 0) {
                  return const SizedBox();
                }
                return Text(
                  value.toInt().toString(),
                  style: const TextStyle(fontSize: 10),
                );
              },
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              interval: bottomInterval,
              getTitlesWidget: (value, meta) {
                final index = value.toInt();
                if (index < 0 || index >= _records.length) {
                  return const SizedBox();
                }
                return Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    DateFormat('MM.dd').format(_records[index].studyDate),
                    style: const TextStyle(fontSize: 10),
                  ),
                );
              },
            ),
          ),
          topTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
          rightTitles: const AxisTitles(
            sideTitles: SideTitles(showTitles: false),
          ),
        ),
        borderData: FlBorderData(show: false),
        lineBarsData: [
          LineChartBarData(
            spots: List.generate(
              scores.length,
              (index) => FlSpot(index.toDouble(), scores[index]),
            ),
            isCurved: true,
            color: Colors.amber,
            barWidth: 4,
            dotData: const FlDotData(show: true),
            belowBarData: BarAreaData(
              show: true,
              color: Colors.amber.withValues(alpha: 0.1),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummary(String title, double value) {
    return Column(
      children: [
        Text(title, style: const TextStyle(color: Colors.grey)),
        const SizedBox(height: 5),
        Text(
          '${value.toStringAsFixed(1)}점',
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
        ),
      ],
    );
  }
}

class _MessageState extends StatelessWidget {
  const _MessageState({
    required this.icon,
    required this.title,
    required this.detail,
    this.actionLabel,
    this.onAction,
  });

  final IconData icon;
  final String title;
  final String detail;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: Colors.grey),
            const SizedBox(height: 12),
            Text(
              title,
              textAlign: TextAlign.center,
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(
              detail,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.grey),
            ),
            if (actionLabel != null && onAction != null) ...[
              const SizedBox(height: 16),
              FilledButton(onPressed: onAction, child: Text(actionLabel!)),
            ],
          ],
        ),
      ),
    );
  }
}
