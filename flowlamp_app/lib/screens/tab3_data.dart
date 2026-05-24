import 'dart:math';
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';

class Tab3Data extends StatefulWidget {
  const Tab3Data({super.key});

  @override
  State<Tab3Data> createState() => _Tab3DataState();
}

class _Tab3DataState extends State<Tab3Data> {
  int _selectedCategoryIndex = 0;
  final List<String> _categories = ['학습 점수', '자세 점수', '총 평균 점수'];

  // 💡 탭마다 서로 다른 데이터를 갖도록 맵(Map)으로 분리
  final Map<int, List<Map<String, dynamic>>> _dataMap = {
    0: List.generate(30, (i) => {"date": DateTime(2026, 5, 1).add(Duration(days: i)), "score": 60.0 + Random().nextDouble() * 40.0}),
    1: List.generate(30, (i) => {"date": DateTime(2026, 5, 1).add(Duration(days: i)), "score": 50.0 + Random().nextDouble() * 30.0}),
    2: List.generate(30, (i) => {"date": DateTime(2026, 5, 1).add(Duration(days: i)), "score": 70.0 + Random().nextDouble() * 20.0}),
  };

  DateTimeRange? _selectedRange;

  @override
  void initState() {
    super.initState();
    _selectedRange = DateTimeRange(
      start: DateTime(2026, 5, 13),
      end: DateTime(2026, 5, 24),
    );
  }

  @override
  Widget build(BuildContext context) {
    // 💡 선택된 탭에 해당하는 데이터만 가져옴
    List<Map<String, dynamic>> currentSource = _dataMap[_selectedCategoryIndex]!;
    
    // 선택된 기간 필터링
    List<Map<String, dynamic>> data = currentSource.where((d) => 
      d['date'].isAfter(_selectedRange!.start.subtract(const Duration(days: 1))) && 
      d['date'].isBefore(_selectedRange!.end.add(const Duration(days: 1)))
    ).toList();

    final scores = data.map((d) => d['score'] as double).toList();
    double maxScore = scores.isNotEmpty ? scores.reduce(max) : 0.0;
    double minScore = scores.isNotEmpty ? scores.reduce(min) : 0.0;
    double avgScore = scores.isNotEmpty ? scores.reduce((a, b) => a + b) / scores.length : 0.0;

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16.0),
          child: OutlinedButton.icon(
            style: OutlinedButton.styleFrom(side: const BorderSide(color: Colors.amber)),
            icon: const Icon(Icons.calendar_month, color: Colors.amber),
            label: Text("${DateFormat('MM.dd').format(_selectedRange!.start)} ~ ${DateFormat('MM.dd').format(_selectedRange!.end)}"),
            onPressed: () async {
              final range = await showDateRangePicker(
                context: context, 
                firstDate: DateTime(2026, 5, 1), 
                lastDate: DateTime(2026, 5, 24),
                initialDateRange: _selectedRange,
                initialEntryMode: DatePickerEntryMode.calendarOnly,
                builder: (context, child) => Theme(data: Theme.of(context).copyWith(colorScheme: const ColorScheme.light(primary: Colors.amber)), child: child!),
              );
              if (range != null) setState(() => _selectedRange = range);
            },
          ),
        ),
        
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16.0),
          child: Row(
            children: List.generate(3, (index) => Expanded(
              child: GestureDetector(
                onTap: () => setState(() => _selectedCategoryIndex = index),
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  margin: const EdgeInsets.symmetric(horizontal: 4),
                  decoration: BoxDecoration(color: _selectedCategoryIndex == index ? Colors.amber : Colors.grey.shade200, borderRadius: BorderRadius.circular(10)),
                  child: Center(child: Text(_categories[index], style: TextStyle(fontWeight: FontWeight.bold, color: _selectedCategoryIndex == index ? Colors.white : Colors.black))),
                ),
              ),
            )),
          ),
        ),
        
        Expanded(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(20, 40, 40, 20),
            child: LineChart(LineChartData(
              minY: 0, maxY: 100,
              gridData: const FlGridData(show: false),
              lineTouchData: LineTouchData(touchTooltipData: LineTouchTooltipData(
                getTooltipItems: (spots) => spots.map((spot) => LineTooltipItem("${spot.y.toStringAsFixed(1)}점", const TextStyle(color: Colors.white))).toList()
              )),
              titlesData: FlTitlesData(
                leftTitles: AxisTitles(sideTitles: SideTitles(
                  showTitles: true, interval: 20, reservedSize: 30, 
                  getTitlesWidget: (v, m) => v == 0 ? const SizedBox() : Text(v.toInt().toString(), style: const TextStyle(fontSize: 10))
                )),
                bottomTitles: AxisTitles(sideTitles: SideTitles(
                  showTitles: true,
                  interval: max(1, (data.length / 5).floorToDouble()),
                  getTitlesWidget: (v, m) {
                    int index = v.toInt();
                    if (index < 0 || index >= data.length) return const SizedBox();
                    return Padding(padding: const EdgeInsets.only(top: 8), child: Text(DateFormat('MM.dd').format(data[index]['date']), style: const TextStyle(fontSize: 10)));
                  },
                )),
                topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
              ),
              borderData: FlBorderData(show: false),
              lineBarsData: [
                LineChartBarData(
                  spots: List.generate(data.length, (i) => FlSpot(i.toDouble(), data[i]['score'])),
                  isCurved: true, color: Colors.amber, barWidth: 4, dotData: const FlDotData(show: true),
                  belowBarData: BarAreaData(show: true, color: Colors.amber.withOpacity(0.1)),
                ),
              ],
            )),
          ),
        ),
        
        Padding(
          padding: const EdgeInsets.all(20.0),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              _buildSummary("최고", "${maxScore.toStringAsFixed(1)}점"),
              _buildSummary("최저", "${minScore.toStringAsFixed(1)}점"),
              _buildSummary("평균", "${avgScore.toStringAsFixed(1)}점"),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSummary(String title, String value) => Column(
    children: [Text(title, style: const TextStyle(color: Colors.grey)), const SizedBox(height: 5), Text(value, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18))],
  );
}