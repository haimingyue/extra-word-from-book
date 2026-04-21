from __future__ import annotations

import unittest

from app.api.routes.vocab_test import create_session, submit_answers
from app.schemas.vocab_test import (
    DurationMode,
    TestResponseValue,
    VocabularyTestAnswer,
    VocabularyTestAnswerRequest,
    VocabularyTestSessionCreateRequest,
)
from app.services.vocab_test_service import VocabularyTestService, load_test_word_bank


class VocabularyTestServiceTestCase(unittest.TestCase):
    def test_word_bank_has_expected_bands(self) -> None:
        bank = load_test_word_bank()
        self.assertEqual(min(bank), 1000)
        self.assertEqual(max(bank), 15000)
        self.assertGreater(len(bank[1000]), 0)
        self.assertGreater(len(bank[5000]), 0)
        sample = bank[3000][0]
        self.assertTrue(sample.meaning)
        self.assertLessEqual(len(sample.meaning), 48)

    def test_duration_modes_return_expected_first_stage_sizes(self) -> None:
        service = VocabularyTestService()
        quick = service.create_session(DurationMode.quick)
        standard = service.create_session(DurationMode.standard)
        deep = service.create_session(DurationMode.deep)
        self.assertEqual(len(quick.questions), 24)
        self.assertEqual(len(standard.questions), 32)
        self.assertEqual(len(deep.questions), 45)
        self.assertTrue(all(question.meaning for question in deep.questions))

    def test_session_can_finish_with_consistent_result(self) -> None:
        service = VocabularyTestService()
        progress = service.create_session(DurationMode.quick)
        while not progress.completed:
            answers = []
            for question in progress.questions:
                response = TestResponseValue.know if question.coca_rank <= 4000 else TestResponseValue.dont_know
                answers.append(VocabularyTestAnswer(question_id=question.question_id, response=response))
            progress = service.submit_answers(progress.session_id, answers)

        self.assertTrue(progress.completed)
        self.assertIsNotNone(progress.result)
        self.assertLessEqual(progress.result.recommended_coca_rank, progress.result.estimated_vocabulary_size)
        self.assertLessEqual(progress.result.estimated_vocabulary_size, progress.result.recommended_coca_rank + 1000)
        self.assertGreaterEqual(progress.result.answered_count, 44)

    def test_deep_mode_requires_stage_three_and_minimum_question_budget(self) -> None:
        service = VocabularyTestService()
        progress = service.create_session(DurationMode.deep)
        self.assertEqual(progress.stage_number, 1)
        total_answered = 0

        progress = service.submit_answers(
            progress.session_id,
            [VocabularyTestAnswer(question_id=item.question_id, response=TestResponseValue.unsure) for item in progress.questions],
        )
        total_answered += 45
        self.assertFalse(progress.completed)
        self.assertEqual(progress.stage_number, 2)

        stage_two_count = len(progress.questions)
        progress = service.submit_answers(
            progress.session_id,
            [VocabularyTestAnswer(question_id=item.question_id, response=TestResponseValue.unsure) for item in progress.questions],
        )
        total_answered += stage_two_count
        self.assertFalse(progress.completed)
        self.assertEqual(progress.stage_number, 3)

        stage_three_count = len(progress.questions)
        progress = service.submit_answers(
            progress.session_id,
            [VocabularyTestAnswer(question_id=item.question_id, response=TestResponseValue.unsure) for item in progress.questions],
        )
        total_answered += stage_three_count
        self.assertTrue(progress.completed)
        self.assertGreaterEqual(total_answered, 125)
        self.assertGreaterEqual(progress.result.answered_count, 125)


class VocabularyTestRouteTestCase(unittest.TestCase):
    def test_route_flow_returns_next_stage(self) -> None:
        created = create_session(VocabularyTestSessionCreateRequest(duration_mode=DurationMode.standard))
        payload = created.data
        self.assertFalse(payload.completed)
        self.assertGreater(len(payload.questions), 0)

        next_stage = submit_answers(
            payload.session_id,
            VocabularyTestAnswerRequest(
                answers=[
                    VocabularyTestAnswer(question_id=item.question_id, response=TestResponseValue.unsure)
                    for item in payload.questions
                ]
            ),
        )
        self.assertIsNotNone(next_stage.data)
        self.assertEqual(next_stage.data.stage_number, 2)
        self.assertTrue(all(item.meaning for item in next_stage.data.questions))


if __name__ == "__main__":
    unittest.main()
