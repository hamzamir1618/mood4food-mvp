import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

// ── Config ─────────────────────────────────────────────────────────────────
const String kApiBase = 'http://localhost:8000';

void main() => runApp(const FipeApp());

class FipeApp extends StatelessWidget {
  const FipeApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'FIPE — Mood4Food',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0D0D1A),
        fontFamily: 'Inter',
        colorSchemeSeed: const Color(0xFF6C63FF),
        useMaterial3: true,
      ),
      home: const DashboardScreen(),
    );
  }
}

// ── Dashboard Screen ───────────────────────────────────────────────────────
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? _blueprint;
  bool _loading = true;
  String? _error;
  double _budgetPriority = 0.3;

  @override
  void initState() {
    super.initState();
    _fetchBlueprint();
  }

  Future<void> _fetchBlueprint() async {
    setState(() { _loading = true; _error = null; });
    try {
      final resp = await http.get(Uri.parse('$kApiBase/decision_blueprint'));
      if (resp.statusCode == 200) {
        setState(() { _blueprint = jsonDecode(resp.body); _loading = false; });
      } else {
        setState(() { _error = 'Server ${resp.statusCode}'; _loading = false; });
      }
    } catch (e) {
      setState(() { _error = e.toString(); _loading = false; });
    }
  }

  Future<void> _onBudgetChanged(double value) async {
    setState(() => _budgetPriority = value);
    try {
      final resp = await http.post(
        Uri.parse('$kApiBase/recalculate'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'w_budget': double.parse(value.toStringAsFixed(2))}),
      );
      if (resp.statusCode == 200) {
        setState(() => _blueprint = jsonDecode(resp.body));
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            // ── Header ──
            SliverToBoxAdapter(child: _buildHeader()),
            // ── Body ──
            SliverFillRemaining(
              hasScrollBody: false,
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _error != null
                      ? _buildError()
                      : _buildContent(),
            ),
          ],
        ),
      ),
    );
  }

  // ── Header ───────────────────────────────────────────────────────────────
  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 28, 24, 8),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF6C63FF), Color(0xFFE040FB)],
              ),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(Icons.restaurant, color: Colors.white, size: 22),
          ),
          const SizedBox(width: 14),
          const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Mood4Food',
                  style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700,
                      color: Colors.white)),
              Text('Decision Engine',
                  style: TextStyle(fontSize: 13, color: Color(0xFF8E8EA0))),
            ],
          ),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.refresh, color: Color(0xFF8E8EA0)),
            onPressed: _fetchBlueprint,
          ),
        ],
      ),
    );
  }

  // ── Error State ──────────────────────────────────────────────────────────
  Widget _buildError() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.cloud_off, size: 48, color: Color(0xFF8E8EA0)),
          const SizedBox(height: 12),
          Text(_error!, style: const TextStyle(color: Color(0xFF8E8EA0))),
          const SizedBox(height: 16),
          FilledButton.icon(
            onPressed: _fetchBlueprint,
            icon: const Icon(Icons.refresh, size: 18),
            label: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  // ── Main Content ─────────────────────────────────────────────────────────
  Widget _buildContent() {
    final dish = _blueprint?['winning_dish'] ?? {};
    final scores = _blueprint?['utility_breakdown'] ?? {};
    final traces = List<String>.from(_blueprint?['xai_traces'] ?? []);

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const SizedBox(height: 16),
          _EquilibriumCard(dish: dish, scores: scores),
          const SizedBox(height: 20),
          _UtilityBars(scores: scores),
          const SizedBox(height: 20),
          _BudgetSlider(
            value: _budgetPriority,
            onChanged: _onBudgetChanged,
          ),
          const SizedBox(height: 20),
          _XaiTraceCard(traces: traces),
          const SizedBox(height: 32),
        ],
      ),
    );
  }
}

// ── Equilibrium Card ───────────────────────────────────────────────────────
class _EquilibriumCard extends StatelessWidget {
  final Map<String, dynamic> dish;
  final Map<String, dynamic> scores;
  const _EquilibriumCard({required this.dish, required this.scores});

  @override
  Widget build(BuildContext context) {
    final name = dish['name'] ?? 'No dish';
    final uTotal = (scores['u_total'] ?? 0.0).toDouble();

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft, end: Alignment.bottomRight,
          colors: [Color(0xFF1A1A2E), Color(0xFF16213E)],
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: const Color(0xFF6C63FF).withOpacity(0.3)),
        boxShadow: [
          BoxShadow(color: const Color(0xFF6C63FF).withOpacity(0.08),
              blurRadius: 24, offset: const Offset(0, 8)),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFF6C63FF).withOpacity(0.15),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Text('EQUILIBRIUM',
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600,
                      color: Color(0xFF6C63FF), letterSpacing: 1.2)),
            ),
            const Spacer(),
            Text('U = ${uTotal.toStringAsFixed(4)}',
                style: const TextStyle(fontSize: 13, color: Color(0xFFE040FB),
                    fontWeight: FontWeight.w600)),
          ]),
          const SizedBox(height: 16),
          Text(name,
              style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w700,
                  color: Colors.white)),
          const SizedBox(height: 6),
          Text('Dish ID: ${dish['dish_id'] ?? '—'}',
              style: const TextStyle(fontSize: 13, color: Color(0xFF8E8EA0))),
        ],
      ),
    );
  }
}

// ── Utility Score Bars ─────────────────────────────────────────────────────
class _UtilityBars extends StatelessWidget {
  final Map<String, dynamic> scores;
  const _UtilityBars({required this.scores});

  @override
  Widget build(BuildContext context) {
    final items = [
      ('Health  U_h', (scores['u_health'] ?? 0.0).toDouble(), const Color(0xFF00E676)),
      ('Budget  U_b', (scores['u_budget'] ?? 0.0).toDouble(), const Color(0xFF40C4FF)),
      ('Taste   U_t', (scores['u_taste'] ?? 0.0).toDouble(), const Color(0xFFE040FB)),
    ];

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A2E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Column(
        children: items.map((item) {
          final (label, value, color) = item;
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(children: [
              SizedBox(width: 90,
                  child: Text(label,
                      style: const TextStyle(fontSize: 12,
                          color: Color(0xFFB0B0C0),
                          fontFamily: 'monospace'))),
              const SizedBox(width: 12),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: value.clamp(0.0, 1.0),
                    minHeight: 8,
                    backgroundColor: Colors.white.withOpacity(0.06),
                    valueColor: AlwaysStoppedAnimation(color),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              SizedBox(width: 48,
                  child: Text(value.toStringAsFixed(4),
                      textAlign: TextAlign.right,
                      style: TextStyle(fontSize: 12, color: color,
                          fontWeight: FontWeight.w600,
                          fontFamily: 'monospace'))),
            ]),
          );
        }).toList(),
      ),
    );
  }
}

// ── Budget Priority Slider ─────────────────────────────────────────────────
class _BudgetSlider extends StatelessWidget {
  final double value;
  final ValueChanged<double> onChanged;
  const _BudgetSlider({required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A2E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Text('Budget Priority',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600,
                    color: Colors.white)),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: const Color(0xFF40C4FF).withOpacity(0.12),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text('w_b = ${value.toStringAsFixed(2)}',
                  style: const TextStyle(fontSize: 12, color: Color(0xFF40C4FF),
                      fontWeight: FontWeight.w600, fontFamily: 'monospace')),
            ),
          ]),
          Slider(
            value: value,
            min: 0.0,
            max: 1.0,
            divisions: 10,
            activeColor: const Color(0xFF40C4FF),
            inactiveColor: Colors.white.withOpacity(0.08),
            onChangeEnd: onChanged,
            onChanged: (_) {},
          ),
          const Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('Relaxed', style: TextStyle(fontSize: 11, color: Color(0xFF8E8EA0))),
              Text('Strict', style: TextStyle(fontSize: 11, color: Color(0xFF8E8EA0))),
            ],
          ),
        ],
      ),
    );
  }
}

// ── XAI Trace Card ─────────────────────────────────────────────────────────
class _XaiTraceCard extends StatelessWidget {
  final List<String> traces;
  const _XaiTraceCard({required this.traces});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1A2E),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withOpacity(0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Icon(Icons.psychology, size: 18, color: Color(0xFFFFAB40)),
            const SizedBox(width: 8),
            const Text('XAI Reasoning Trace',
                style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600,
                    color: Colors.white)),
            const Spacer(),
            Text('${traces.length} steps',
                style: const TextStyle(fontSize: 12, color: Color(0xFF8E8EA0))),
          ]),
          const SizedBox(height: 14),
          ...traces.map((t) => Padding(
            padding: const EdgeInsets.only(bottom: 6),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('› ', style: TextStyle(color: Color(0xFF6C63FF),
                    fontFamily: 'monospace', fontSize: 12)),
                Expanded(
                  child: Text(t,
                      style: const TextStyle(fontSize: 12,
                          color: Color(0xFFB0B0C0), fontFamily: 'monospace',
                          height: 1.5)),
                ),
              ],
            ),
          )),
        ],
      ),
    );
  }
}
