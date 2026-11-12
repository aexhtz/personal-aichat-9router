import unittest

from personal_ai.chat import SYSTEM_PROMPT, trim_history


class TrimHistoryTests(unittest.TestCase):
    def test_preserves_system_and_newest_complete_turns(self):
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for turn in range(5):
            messages.extend([
                {"role": "user", "content": f"question {turn}"},
                {"role": "assistant", "content": f"answer {turn}"},
            ])

        trim_history(messages, max_messages=4)

        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual([message["content"] for message in messages[1:]], [
            "question 3", "answer 3", "question 4", "answer 4",
        ])

    def test_drops_orphaned_assistant_message(self):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "old"},
            {"role": "assistant", "content": "old answer"},
            {"role": "user", "content": "new"},
            {"role": "assistant", "content": "new answer"},
        ]

        trim_history(messages, max_messages=3)

        self.assertEqual(messages[1:], [
            {"role": "user", "content": "new"},
            {"role": "assistant", "content": "new answer"},
        ])


if __name__ == "__main__":
    unittest.main()
