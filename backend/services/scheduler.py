"""
Daily summary scheduler.

Fires automatically at DAILY_SUMMARY_HOUR:DAILY_SUMMARY_MINUTE (default 18:00)
to send the AI-generated daily lesson summary to both Google Chat (students)
and Zalo clone UI (parents).

Also exposes shared demo lesson content constants:

- ``DEMO_LESSON_CONTENT`` — raw lesson data used as AI context fallback
- ``DEMO_LESSON_CONTENT_PARENTS`` — pre-formatted parent-facing summary (Zalo)
- ``DEMO_LESSON_CONTENT_STUDENTS`` — pre-formatted student-facing summary (Google Chat)

These constants are imported by the Zalo route and the Google Chat listener
to serve ``/demosum`` responses without calling the LLM.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional

from config import settings
from utils.logger import logger


# ===== Demo lesson content =====

# Raw lesson data — used internally and as AI context fallback
DEMO_LESSON_CONTENT = """
TOÁN — Phân số (Tuần 12)
- Cộng phân số khác mẫu: quy đồng mẫu số rồi cộng tử số
  Ví dụ: 1/3 + 1/4 = 4/12 + 3/12 = 7/12
- Trừ phân số khác mẫu: quy đồng rồi trừ tử số
  Ví dụ: 3/4 − 1/3 = 9/12 − 4/12 = 5/12
- BTVN (hạn thứ 6): 2/5 + 1/3 ; 5/6 − 1/4

KHOA HỌC TỰ NHIÊN — Hệ tiêu hóa
- Đường đi: miệng → thực quản → dạ dày → ruột non → ruột già
- BTVN: Vẽ sơ đồ đường đi của thức ăn

TIẾNG ANH — Conditional Type 1
- If + S + V(hiện tại đơn), S + will + V(nguyên mẫu)
- BTVN: Viết 5 câu điều kiện loại 1 về kế hoạch của em"""

# Demo summary for PARENTS (Zalo) — formal tone
DEMO_LESSON_CONTENT_PARENTS = """
Bố mẹ các con thân mến,
Cô Hana xin gửi lại nội dung buổi học ngày hôm nay của các con ạ:

1. TOÁN - Cộng, trừ phân số khác mẫu số
- Kiến thức: Để cộng hoặc trừ hai phân số khác mẫu, ta quy đồng mẫu số rồi cộng hoặc trừ tử số. Quy đồng mẫu số là tìm bội chung nhỏ nhất (BCNN) của hai mẫu số.
- Bài tập về nhà: Bài 1: Tính 2/5 + 1/3; Bài 2: Tính 5/6 - 1/4; Bài 3: An có 3/4 cái bánh, An ăn 1/3 cái bánh. Hỏi An còn bao nhiêu?
- Hạn nộp/Lưu ý: Nộp bài tập Toán trước Thứ 6 tuần 12.

2. KHOA HỌC TỰ NHIÊN - Các cơ quan trong hệ tiêu hóa
- Kiến thức: Hệ tiêu hóa gồm: miệng → thực quản → dạ dày → ruột non → ruột già. Miệng nhai nghiền, dạ dày co bóp và tiết dịch vị, ruột non hấp thụ chất dinh dưỡng, ruột già hấp thụ nước.
- Bài tập về nhà: Vẽ sơ đồ đường đi của thức ăn trong cơ thể.
- Hạn nộp/Lưu ý: Kiểm tra Khoa học vào Thứ 4.

3. TIẾNG ANH - Câu điều kiện loại 1 (First Conditional)
- Kiến thức: Cấu trúc: If + S + V(hiện tại đơn), S + will + V(nguyên mẫu).
- Bài tập về nhà: Exercise 1: Complete the sentences with the correct form; Exercise 2: Write 5 sentences about your plans using "If...".
- Hạn nộp/Lưu ý: Không có.

Kính mong bố mẹ hỗ trợ nhắc nhở các con hoàn thành bài tập đầy đủ giúp cô ạ.
Cảm ơn bố mẹ các con đã đọc tin ạ!"""

# Demo summary for STUDENTS (Google Chat) — friendly tone
DEMO_LESSON_CONTENT_STUDENTS = """
Các con thân mến,
Cô Hana gửi lại nội dung buổi học ngày hôm nay của các con:

1. TOÁN - Cộng, trừ phân số khác mẫu số
- Kiến thức: Để cộng hoặc trừ hai phân số khác mẫu, ta quy đồng mẫu số rồi cộng hoặc trừ tử số. Quy đồng mẫu số là tìm bội chung nhỏ nhất (BCNN) của hai mẫu số.
- Bài tập về nhà: Bài 1: Tính 2/5 + 1/3; Bài 2: Tính 5/6 - 1/4; Bài 3: An có 3/4 cái bánh, An ăn 1/3 cái bánh. Hỏi An còn bao nhiêu?
- Hạn nộp/Lưu ý: Nộp bài tập Toán trước Thứ 6 tuần 12.

2. KHOA HỌC TỰ NHIÊN - Các cơ quan trong hệ tiêu hóa
- Kiến thức: Hệ tiêu hóa gồm: miệng → thực quản → dạ dày → ruột non → ruột già. Miệng nhai nghiền, dạ dày co bóp và tiết dịch vị, ruột non hấp thụ chất dinh dưỡng, ruột già hấp thụ nước.
- Bài tập về nhà: Vẽ sơ đồ đường đi của thức ăn trong cơ thể.
- Hạn nộp/Lưu ý: Kiểm tra Khoa học vào Thứ 4.

3. TIẾNG ANH - Câu điều kiện loại 1 (First Conditional)
- Kiến thức: Cấu trúc: If + S + V(hiện tại đơn), S + will + V(nguyên mẫu).
- Bài tập về nhà: Exercise 1: Complete the sentences with the correct form; Exercise 2: Write 5 sentences about your plans using "If...".
- Hạn nộp/Lưu ý: Không có.

Các con nhớ hoàn thành bài tập đầy đủ nhé!"""


# ===== Trigger helper =====

async def trigger_daily_summary_demo(
    content: Optional[str] = None,
    channels: Optional[list[str]] = None,
) -> None:
    """
    Send the demo daily summary to the requested channels.

    Args:
        content:  Plain-text lesson content.  Defaults to DEMO_LESSON_CONTENT.
        channels: List of channel names to send to, e.g. ``["zalo"]`` or
                  ``["gchat", "zalo"]``.  ``None`` means *all* channels.
    """
    text = content or DEMO_LESSON_CONTENT

    send_gchat = channels is None or "gchat" in channels
    send_zalo = channels is None or "zalo" in channels

    date_str = datetime.now().strftime("%d/%m/%Y")

    # Google Chat — post via webhook / notification service
    if send_gchat:
        try:
            from services.notification import (
                Notification,
                NotificationType,
                NotificationChannel,
                StudentInfo,
                NotificationService,
            )

            notification = Notification(
                notification_type=NotificationType.DAILY_SUMMARY,
                channel=NotificationChannel.GOOGLE_CHAT,
                student=StudentInfo(
                    student_id="student-demo",
                    name="Demo",
                    grade="4",
                    class_name="4B5",
                ),
                title=f"Daily Summary — {date_str}",
                message=text,
            )

            svc = NotificationService()
            result = await svc.send_notification(notification)
            if result.success:
                logger.info("[SCHEDULER] Daily summary sent to Google Chat")
            else:
                logger.warning(
                    f"[SCHEDULER] Google Chat send failed: {result.error_message}"
                )
        except Exception as e:
            logger.error(f"[SCHEDULER] Google Chat daily summary error: {e}")

    # Zalo — post via ZaloNotifier (in-memory store → REST polling)
    if send_zalo:
        try:
            from services.notification.zalo_notifier import ZaloNotifier
            from services.notification.models import (
                Notification as ZNotification,
                NotificationType as ZType,
                NotificationChannel as ZChannel,
                StudentInfo as ZStudent,
                ParentInfo as ZParent,
            )

            notification = ZNotification(
                notification_type=ZType.DAILY_SUMMARY,
                channel=ZChannel.ZALO,
                student=ZStudent(
                    student_id="student-demo",
                    name="Alex",
                    grade="4",
                    class_name="4B5",
                ),
                parent=ZParent(
                    parent_id="parent-demo",
                    name="Phụ huynh Alex",
                ),
                title=f"Daily Summary — {date_str}",
                message=text,
            )

            notifier = ZaloNotifier(enabled=True)
            result = await notifier.send(notification)
            if result.success:
                logger.info("[SCHEDULER] Daily summary sent to Zalo")
            else:
                logger.warning(
                    f"[SCHEDULER] Zalo send failed: {result.error_message}"
                )
        except Exception as e:
            logger.error(f"[SCHEDULER] Zalo daily summary error: {e}")


# ===== Scheduler class =====

class DailySummaryScheduler:
    """
    Pure-asyncio background loop that fires ``trigger_daily_summary_demo``
    once per day at the configured hour/minute.
    """

    def __init__(self, hour: int = 18, minute: int = 0):
        self._hour = hour
        self._minute = minute
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def seconds_until_next_fire(self) -> float:
        """Return seconds from *now* until the next scheduled fire time."""
        now = datetime.now()
        target = now.replace(
            hour=self._hour, minute=self._minute, second=0, microsecond=0,
        )
        if target <= now:
            target += timedelta(days=1)
        return (target - now).total_seconds()

    async def _loop(self) -> None:
        """Background loop: sleep until fire time, trigger, repeat."""
        logger.info(
            f"[SCHEDULER] Daily summary scheduled at "
            f"{self._hour:02d}:{self._minute:02d} every day"
        )

        while self._running:
            try:
                delay = self.seconds_until_next_fire()
                logger.info(
                    f"[SCHEDULER] Next fire in {delay:.0f}s "
                    f"({delay / 3600:.1f}h)"
                )
                await asyncio.sleep(delay)

                if not self._running:
                    break

                logger.info("[SCHEDULER] Firing daily summary…")
                await trigger_daily_summary_demo()

            except asyncio.CancelledError:
                logger.info("[SCHEDULER] Loop cancelled")
                break
            except Exception as e:
                logger.error(f"[SCHEDULER] Loop error: {e}")
                await asyncio.sleep(60)  # back-off on unexpected errors

    def start(self) -> None:
        """Start the scheduler as a background asyncio task."""
        if self._running:
            logger.warning("[SCHEDULER] Already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("[SCHEDULER] Started")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("[SCHEDULER] Stopped")


# ===== Singleton =====

_scheduler: Optional[DailySummaryScheduler] = None


def get_scheduler() -> DailySummaryScheduler:
    """Get or create the global DailySummaryScheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = DailySummaryScheduler(
            hour=settings.DAILY_SUMMARY_HOUR,
            minute=settings.DAILY_SUMMARY_MINUTE,
        )
    return _scheduler
