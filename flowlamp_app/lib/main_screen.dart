import 'package:flutter/material.dart';
import 'screens/tab1_control.dart';
import 'screens/tab2_routine.dart';
import 'screens/tab3_data.dart';   // 💡 원래 이름 그대로
import 'screens/tab4_manual.dart'; // 💡 원래 이름 그대로

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int _selectedIndex = 0;
  final List<String> _titles = ['램프 제어', '알람 및 루틴', '데이터', '수동 조정'];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F5F5),
      appBar: AppBar(
        title: Text(_titles[_selectedIndex], style: const TextStyle(fontWeight: FontWeight.bold)),
        centerTitle: true,
        backgroundColor: Colors.white,
        elevation: 1,
      ),
      body: IndexedStack(
        index: _selectedIndex,
        children: [
          LampControlTab(),  
          AlarmRoutineTab(),
          Tab3Data(),           
          Tab4Manual(),      
        ],
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _selectedIndex,
        onTap: (index) => setState(() => _selectedIndex = index),
        type: BottomNavigationBarType.fixed,
        selectedItemColor: Colors.amber,
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.lightbulb_outline), label: '램프 제어'),
          BottomNavigationBarItem(icon: Icon(Icons.alarm), label: '알람 및 루틴'),
          BottomNavigationBarItem(icon: Icon(Icons.bar_chart), label: '데이터'),
          BottomNavigationBarItem(icon: Icon(Icons.tune), label: '수동 조정'),
        ],
      ),
    );
  }
}