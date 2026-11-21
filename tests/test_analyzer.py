import unittest

from src.propagation_analyzer import analyze_run, summarize_runs


class AnalyzerTests(unittest.TestCase):
    def test_detects_propagation_and_contaminated_final_output(self):
        events = [
            {
                "run_id": "r1", "event_id": "a", "timestamp": "2026-01-01T00:00:00Z",
                "event_type": "tool_result", "agent": "researcher",
                "injected_fault": True, "fault_type": "semantic_corruption",
            },
            {
                "run_id": "r1", "event_id": "b", "timestamp": "2026-01-01T00:00:01Z",
                "event_type": "agent_message", "agent": "analyst",
                "parent_event_id": "a", "consumed_faulty_information": True,
            },
            {
                "run_id": "r1", "event_id": "c", "timestamp": "2026-01-01T00:00:02Z",
                "event_type": "final_output", "agent": "writer",
                "parent_event_id": "b", "correctness": False,
            },
        ]
        result = analyze_run(events)
        self.assertEqual(result["root_cause_event_id"], "a")
        self.assertTrue(result["fault_propagated"])
        self.assertTrue(result["final_output_contaminated"])
        self.assertEqual(result["downstream_agents"], ["analyst"])

    def test_no_propagation_when_fault_is_contained(self):
        events = [
            {
                "run_id": "r2", "event_id": "a", "timestamp": "2026-01-01T00:00:00Z",
                "event_type": "tool_result", "agent": "researcher",
                "injected_fault": True,
            },
            {
                "run_id": "r2", "event_id": "b", "timestamp": "2026-01-01T00:00:01Z",
                "event_type": "agent_message", "agent": "analyst",
                "parent_event_id": "a",
            },
            {
                "run_id": "r2", "event_id": "c", "timestamp": "2026-01-01T00:00:02Z",
                "event_type": "final_output", "agent": "writer",
                "parent_event_id": "b", "correctness": True,
            },
        ]
        result = analyze_run(events)
        self.assertFalse(result["fault_propagated"])

    def test_summary_denominator_is_injected_runs(self):
        results = [
            {"injected_fault": True, "fault_propagated": True, "has_observable_failure": True,
             "final_output_contaminated": True},
            {"injected_fault": True, "fault_propagated": False, "has_observable_failure": True,
             "final_output_contaminated": False},
            {"injected_fault": False, "fault_propagated": False, "has_observable_failure": False,
             "final_output_contaminated": False},
        ]
        summary = summarize_runs(results)
        self.assertEqual(summary["fault_injected_runs"], 2)
        self.assertEqual(summary["fault_propagated_runs"], 1)
        self.assertEqual(summary["fault_propagation_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()
