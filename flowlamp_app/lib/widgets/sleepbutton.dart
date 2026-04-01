import 'package:flutter/material.dart';

class SleepingButton extends StatefulWidget {
  const SleepingButton({super.key});

  @override
  State<SleepingButton> createState() => _SleepingButtonState();
}

class _SleepingButtonState extends State<SleepingButton> {
  bool isOn = true;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 20).copyWith(top:10),
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 50),
      decoration: BoxDecoration(
        color: const Color(0xFFF2F2F2),
        borderRadius: BorderRadius.circular(28),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.12),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Center(
            child: Text(
              "Posture & Sleeping",
              style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: Colors.black87,
              ),
            ),
          ),
          const SizedBox(height: 18),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: [
              Icon(
                Icons.airline_seat_recline_normal,
                size: 70,
                color: Colors.blueGrey,
              ),
              GestureDetector(
                onTap: () {
                  setState(() {
                    isOn = !isOn;
                  });
                },
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 130,
                  height: 62,
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                  decoration: BoxDecoration(
                    color: isOn ? const Color(0xFF3B3B3B) : Colors.grey.shade400,
                    borderRadius: BorderRadius.circular(40),
                  ),
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      Align(
                        alignment: isOn
                            ? Alignment.centerRight
                            : Alignment.centerLeft,
                        child: Container(
                          width: 50,
                          height: 50,
                          decoration: const BoxDecoration(
                            color: Color(0xFFE8E8E8),
                            shape: BoxShape.circle,
                          ),
                        ),
                      ),
                      Align(
                        alignment: isOn
                            ? Alignment.centerLeft
                            : Alignment.centerRight,
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 18),
                          child: Text(
                            isOn ? "ON" : "OFF",
                            style: const TextStyle(
                              fontSize: 20,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}