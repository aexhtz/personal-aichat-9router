import unittest
from unittest.mock import Mock

from personal_ai import chat


class TrimHistoryTests(unittest.TestCase):
    def test_preserves_system_and_newest_complete_turns(self):
        messages = [{"role": "system", "content": chat.SYSTEM_PROMPT}]
        for turn in range(5):
            messages.extend([
                {"role": "user", "content": f"question {turn}"},
                {"role": "assistant", "content": f"answer {turn}"},
            ])

        chat.trim_history(messages, max_messages=4)

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual([message["content"] for message in messages[1:]], [
            "question 3", "answer 3", "question 4", "answer 4",
        ])

    def test_drops_orphaned_assistant_message(self):
        messages = [
            {"role": "system", "content": chat.SYSTEM_PROMPT},
            {"role": "user", "content": "old"},
            {"role": "assistant", "content": "old answer"},
            {"role": "user", "content": "new"},
            {"role": "assistant", "content": "new answer"},
        ]

        chat.trim_history(messages, max_messages=3)

        self.assertEqual(messages[1:], [
            {"role": "user", "content": "new"},
            {"role": "assistant", "content": "new answer"},
        ])


class AiLabelTests(unittest.TestCase):
    def test_label_includes_selected_combo(self):
        self.assertEqual(chat._ai_label("9router-deepseek"), "AI 9router-deepseek")


class GetCombosTests(unittest.TestCase):
    def test_returns_only_9router_combos(self):
        client = Mock()
        client.models.list.return_value.data = [
            Mock(id="9router-gemini"),
            Mock(id="cx/gpt-6-luna"),
            Mock(id="9router-gptcontext1m"),
        ]

        self.assertEqual(chat.get_combos(client), ["9router-gemini", "9router-gptcontext1m"])


class ChooseComboTests(unittest.TestCase):
    def test_enter_selects_default(self):
        self.assertEqual(chat.choose_combo(["combo-a", "combo-b"], "combo-b", lambda _: ""), "combo-b")

    def test_number_selects_combo(self):
        self.assertEqual(chat.choose_combo(["combo-a", "combo-b"], "combo-a", lambda _: "2"), "combo-b")

    def test_manual_combo_when_model_list_is_unavailable(self):
        self.assertEqual(chat.choose_combo([], "default-model", lambda _: "custom-combo"), "custom-combo")


class SaveHistoryTests(unittest.TestCase):
    def test_saves_user_and_assistant_messages(self):
        messages = [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "halo AI"},
            {"role": "assistant", "content": "halo manusia"},
        ]
        test_file = "test_export_tmp.txt"
        chat.save_history(messages, test_file)

        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()

        import os
        if os.path.exists(test_file):
            os.remove(test_file)

        self.assertIn("[USER]\nhalo AI", content)
        self.assertIn("[ASSISTANT]\nhalo manusia", content)
        self.assertNotIn("system prompt", content)


if __name__ == "__main__":
    unittest.main()
