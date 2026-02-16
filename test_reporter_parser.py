import unittest
from aegis_reporter import parse_report, generate_message

class TestAegisReporter(unittest.TestCase):

    def setUp(self):
        # Mocking a row from the Google Sheet
        # [date, price, fng, prob%, decision, long_term, commentary]

        self.commentary = """[🎯 타점 분석 (Timeframe Zone)]
⚡ 단기 (1~2주): 매수 $1.23 / 매도 $1.45
🌊 중기 (1~3개월): 매집 $1.10 / 익절 $1.80
🌌 장기 (6개월+): 최후선 $0.90 / 목표 $5.89

[🤖 DNN & 선물 지표]
- 확률: 75.00% / 롱숏: 2.80 / 펀딩: 0.0600%"""

        self.row = [
            "2023-10-27",
            "1.25",
            "60",
            "75.00%",
            "분석 완료",
            "상승",
            self.commentary
        ]

    def test_parse_report(self):
        data = parse_report(self.row)

        self.assertIsNotNone(data)
        self.assertEqual(data['date'], "2023-10-27")
        self.assertEqual(data['price'], "1.25")
        self.assertEqual(data['prob'], "75.00")
        self.assertEqual(data['long_term'], "상승")

        # Check parsed values from commentary
        self.assertEqual(data['ls_ratio'], 2.80)
        self.assertEqual(data['funding_rate'], 0.0600)

        self.assertEqual(data['st_buy'], "1.23")
        self.assertEqual(data['st_sell'], "1.45")
        self.assertEqual(data['mt_buy'], "1.10")
        self.assertEqual(data['mt_sell'], "1.80")
        self.assertEqual(data['lt_buy'], "0.90")
        self.assertEqual(data['lt_sell'], "5.89")

    def test_generate_message(self):
        data = parse_report(self.row)
        message = generate_message(data)

        # Check for key phrases
        self.assertIn("🚀 **강력 매수 (Strong Buy)**", message) # prob >= 70
        self.assertIn("⚠️ **롱 스퀴즈 경보**", message) # ls_ratio > 2.5
        self.assertIn("⚠️ **펀딩비 과열**", message) # funding_rate > 0.05
        self.assertIn("⚡ **단기 (1~2주)**: 진입 $1.23 / 목표 $1.45", message)
        self.assertIn("현재 추세: **상승**", message)

if __name__ == '__main__':
    unittest.main()
