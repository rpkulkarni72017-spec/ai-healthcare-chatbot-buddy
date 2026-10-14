import unittest

from fastapi.testclient import TestClient

from app import EMERGENCY_REPLY, app, respond_to_message


class ChatResponseTests(unittest.TestCase):
    def test_greeting_gets_a_conversational_response(self) -> None:
        response = respond_to_message("Hi")

        self.assertIn("Hi, I'm Buddy", response.reply)
        self.assertTrue(response.suggestions)

    def test_user_can_ask_what_buddy_supports(self) -> None:
        response = respond_to_message("What can you help me with?")

        self.assertIn("stomach bugs", response.reply)
        self.assertIn("can't diagnose", response.reply)

    def test_matches_general_health_topics_and_includes_sources(self) -> None:
        response = respond_to_message("What can I do for a cold?")

        self.assertEqual(response.topic, "Common cold")
        self.assertIn("When to get help:", response.reply)
        self.assertTrue(response.sources)
        self.assertEqual(response.safety_level, "general")

    def test_tailors_answer_to_multiple_symptoms_and_combines_guidance(self) -> None:
        response = respond_to_message("I have a runny nose and my throat hurts")

        self.assertEqual(response.topic, "Common cold + Sore throat")
        self.assertIn("You mentioned runny nose, my throat hurts", response.reply)
        self.assertIn("Common cold:", response.reply)
        self.assertIn("Sore throat:", response.reply)
        self.assertGreaterEqual(len(response.sources), 2)

    def test_understands_common_paraphrases(self) -> None:
        response = respond_to_message("My head is pounding")

        self.assertEqual(response.topic, "Headache")
        self.assertIn("head is pounding", response.reply)

    def test_detects_emergency_language_before_topic_matching(self) -> None:
        response = respond_to_message("I have a headache and can’t breathe")

        self.assertEqual(response.safety_level, "emergency")
        self.assertEqual(response.reply, EMERGENCY_REPLY)
        self.assertFalse(response.sources)

    def test_detects_apostrophe_emergency_phrases(self) -> None:
        response = respond_to_message("I can't breathe")

        self.assertEqual(response.safety_level, "emergency")

    def test_negated_emergency_symptom_does_not_trigger_emergency_response(self) -> None:
        response = respond_to_message("I have a headache but no chest pain")

        self.assertNotEqual(response.safety_level, "emergency")
        self.assertEqual(response.topic, "Headache")

    def test_does_not_recommend_medicine_doses(self) -> None:
        response = respond_to_message("How much medicine should I take?")

        self.assertEqual(response.safety_level, "urgent")
        self.assertIn("can't safely recommend a medicine dose", response.reply)

    def test_water_quantity_question_is_not_mistaken_for_medicine_dosing(self) -> None:
        response = respond_to_message("How much water should I drink?")

        self.assertEqual(response.topic, "Hydration")
        self.assertEqual(response.safety_level, "general")

    def test_unknown_questions_get_a_clear_scope_boundary(self) -> None:
        response = respond_to_message("Can you diagnose my rash?")

        self.assertIsNone(response.topic)
        self.assertIn("What symptom or health topic", response.reply)
        self.assertIn("healthcare professional", response.reply)

    def test_api_uses_recent_chat_context_for_follow_up(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/api/chat",
            json={
                "message": "How long will it last?",
                "history": [{"role": "user", "content": "I have a cold"}],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("1 to 2 weeks", response.json()["reply"])

    def test_api_keeps_context_across_follow_up_chain(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/api/chat",
            json={
                "message": "What if it gets worse?",
                "history": [
                    {"role": "user", "content": "I have a cold"},
                    {"role": "assistant", "content": "General cold guidance."},
                    {"role": "user", "content": "How long will it last?"},
                    {"role": "assistant", "content": "About 1 to 2 weeks."},
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("common cold", response.json()["topic"].lower())
        self.assertIn("get worse", response.json()["reply"].lower())


if __name__ == "__main__":
    unittest.main()
