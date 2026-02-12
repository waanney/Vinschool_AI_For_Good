"""
Populate Milvus with mock educational content for testing.
Run this after init_milvus.py to add sample data.
"""

import asyncio
from uuid import uuid4
from datetime import datetime

from domain.models.document import Document, DocumentType
from agents.content_processor.agent import ContentProcessorAgent
from utils.logger import logger


# Mock educational content about mathematics
MOCK_DOCUMENTS = [
    {
        "title": "Phân số - Cộng và Trừ Phân số",
        "subject": "Mathematics",
        "grade": 9,
        "content": """
# Cộng và Trừ Phân Số

## 1. Cộng phân số cùng mẫu

Khi cộng hai phân số có cùng mẫu số, ta giữ nguyên mẫu số và cộng các tử số.

Công thức: a/c + b/c = (a+b)/c

Ví dụ: 2/7 + 3/7 = (2+3)/7 = 5/7

## 2. Cộng phân số khác mẫu

Để cộng hai phân số khác mẫu, ta làm theo các bước sau:

**Bước 1:** Tìm mẫu số chung (thường là BCNN của hai mẫu)
**Bước 2:** Quy đồng mẫu số - nhân cả tử và mẫu với số thích hợp
**Bước 3:** Cộng các tử số, giữ nguyên mẫu số chung
**Bước 4:** Rút gọn phân số (nếu được)

### Ví dụ chi tiết:
Tính: 1/3 + 1/4

- Bước 1: BCNN(3,4) = 12
- Bước 2: Quy đồng:
  - 1/3 = (1×4)/(3×4) = 4/12
  - 1/4 = (1×3)/(4×3) = 3/12
- Bước 3: 4/12 + 3/12 = 7/12
- Bước 4: 7/12 đã tối giản

Đáp số: 1/3 + 1/4 = 7/12

## 3. Trừ phân số

Trừ phân số tương tự như cộng, nhưng ta lấy hiệu thay vì tổng.

- Cùng mẫu: a/c - b/c = (a-b)/c
- Khác mẫu: Quy đồng rồi trừ tử số

Ví dụ: 5/6 - 1/3 = 5/6 - 2/6 = 3/6 = 1/2
"""
    },
    {
        "title": "Phân số - Nhân và Chia Phân số",
        "subject": "Mathematics",
        "grade": 9,
        "content": """
# Nhân và Chia Phân Số

## 1. Nhân phân số

Để nhân hai phân số, ta nhân tử với tử, mẫu với mẫu.

Công thức: a/b × c/d = (a×c)/(b×d)

### Ví dụ:
- 2/3 × 4/5 = (2×4)/(3×5) = 8/15
- 1/2 × 3/7 = 3/14

### Mẹo tính nhanh:
Có thể rút gọn chéo trước khi nhân:
- 4/9 × 3/8 = (4×3)/(9×8) = 12/72 = 1/6
- Hoặc: 4/9 × 3/8 = (4÷4)/(9÷3) × (3÷3)/(8÷4) = 1/3 × 1/2 = 1/6

## 2. Chia phân số

Để chia một phân số cho phân số khác, ta nhân phân số thứ nhất với phân số nghịch đảo của phân số thứ hai.

Công thức: a/b ÷ c/d = a/b × d/c = (a×d)/(b×c)

### Ví dụ:
- 2/3 ÷ 4/5 = 2/3 × 5/4 = 10/12 = 5/6
- 1/2 ÷ 3/4 = 1/2 × 4/3 = 4/6 = 2/3

### Phân số nghịch đảo:
- Nghịch đảo của a/b là b/a
- Ví dụ: Nghịch đảo của 3/4 là 4/3
- Lưu ý: Không có nghịch đảo của 0

## 3. Tính chất quan trọng

- a/b × 1 = a/b (nhân với 1 không đổi)
- a/b × 0 = 0 (nhân với 0 được 0)
- a/b ÷ 1 = a/b (chia cho 1 không đổi)
- a/b × b/a = 1 (nhân với nghịch đảo được 1)
"""
    },
    {
        "title": "Phân số - So sánh Phân số",
        "subject": "Mathematics",
        "grade": 9,
        "content": """
# So Sánh Phân Số

## 1. So sánh phân số cùng mẫu

Khi hai phân số có cùng mẫu số dương, phân số nào có tử số lớn hơn thì lớn hơn.

Ví dụ: 5/7 > 3/7 (vì 5 > 3)

## 2. So sánh phân số cùng tử

Khi hai phân số có cùng tử số dương, phân số nào có mẫu số nhỏ hơn thì lớn hơn.

Ví dụ: 3/4 > 3/5 (vì 4 < 5)

## 3. So sánh phân số khác mẫu khác tử

**Phương pháp 1: Quy đồng mẫu số**
- Tìm BCNN của các mẫu
- Quy đồng và so sánh tử số

Ví dụ: So sánh 2/3 và 3/4
- BCNN(3,4) = 12
- 2/3 = 8/12; 3/4 = 9/12
- Vì 8 < 9 nên 2/3 < 3/4

**Phương pháp 2: Quy đồng tử số**
- Tìm BCNN của các tử
- Quy đồng và so sánh mẫu số (ngược lại)

**Phương pháp 3: So sánh với số trung gian**
- Thường dùng 0, 1/2, 1 làm số trung gian

Ví dụ: So sánh 4/9 và 5/11
- 4/9 < 1/2 (vì 4×2 = 8 < 9)
- 5/11 > 1/2 (vì 5×2 = 10 < 11, nhưng 5/11 gần 1/2)
- Cần tính chính xác hơn: quy đồng được 44/99 và 45/99
- Vậy 4/9 < 5/11

## 4. Phân số âm

- Phân số âm luôn nhỏ hơn phân số dương
- So sánh hai phân số âm: phân số nào có giá trị tuyệt đối nhỏ hơn thì lớn hơn
  
Ví dụ: -1/3 > -1/2 (vì 1/3 < 1/2)
"""
    },
    {
        "title": "Phương trình bậc nhất",
        "subject": "Mathematics", 
        "grade": 9,
        "content": """
# Phương Trình Bậc Nhất Một Ẩn

## 1. Định nghĩa

Phương trình bậc nhất một ẩn có dạng: ax + b = 0, trong đó a ≠ 0

Ví dụ: 2x + 3 = 0, 5x - 10 = 0

## 2. Cách giải

**Bước 1:** Chuyển vế các hạng tử chứa ẩn về một vế, các hạng tử tự do về vế kia
**Bước 2:** Thu gọn
**Bước 3:** Chia cả hai vế cho hệ số của ẩn

### Ví dụ:
Giải phương trình: 3x + 5 = 14

- Bước 1: 3x = 14 - 5
- Bước 2: 3x = 9  
- Bước 3: x = 9/3 = 3

Vậy x = 3

## 3. Phương trình đưa về dạng ax + b = 0

Các bước giải:
1. Bỏ dấu ngoặc (nếu có)
2. Chuyển vế và thu gọn
3. Giải phương trình bậc nhất

### Ví dụ:
2(x - 1) + 3 = x + 4

- Bỏ ngoặc: 2x - 2 + 3 = x + 4
- Thu gọn: 2x + 1 = x + 4
- Chuyển vế: 2x - x = 4 - 1
- Giải: x = 3

## 4. Phương trình tích

Dạng: A(x).B(x) = 0

Phương pháp: A(x).B(x) = 0 ⇔ A(x) = 0 hoặc B(x) = 0

Ví dụ: (x - 2)(x + 3) = 0
⇔ x - 2 = 0 hoặc x + 3 = 0
⇔ x = 2 hoặc x = -3
"""
    },
    {
        "title": "Hệ phương trình bậc nhất hai ẩn",
        "subject": "Mathematics",
        "grade": 9,
        "content": """
# Hệ Phương Trình Bậc Nhất Hai Ẩn

## 1. Định nghĩa

Hệ phương trình bậc nhất hai ẩn có dạng:
{ax + by = c
{a'x + b'y = c'

## 2. Phương pháp thế

**Các bước:**
1. Từ một phương trình, biểu diễn ẩn này theo ẩn kia
2. Thế vào phương trình còn lại để được phương trình một ẩn
3. Giải phương trình vừa tìm được
4. Suy ra ẩn còn lại

### Ví dụ:
{x + y = 5
{2x - y = 1

Từ PT(1): y = 5 - x
Thế vào PT(2): 2x - (5 - x) = 1
⇒ 2x - 5 + x = 1
⇒ 3x = 6
⇒ x = 2

Thế x = 2 vào y = 5 - x: y = 5 - 2 = 3

Vậy hệ có nghiệm (x, y) = (2, 3)

## 3. Phương pháp cộng đại số

**Các bước:**
1. Nhân hai vế của mỗi phương trình với số thích hợp (nếu cần) để hệ số của một ẩn nào đó trong hai phương trình bằng nhau hoặc đối nhau
2. Cộng hoặc trừ từng vế hai phương trình để được phương trình mới với một ẩn
3. Giải phương trình một ẩn
4. Suy ra ẩn còn lại

### Ví dụ:
{2x + 3y = 8
{3x - 2y = 1

Nhân PT(1) với 2: 4x + 6y = 16
Nhân PT(2) với 3: 9x - 6y = 3

Cộng hai PT: 13x = 19 ⇒ x = 19/13
Thế vào tìm y...

## 4. Ứng dụng

Hệ phương trình thường dùng để giải các bài toán thực tế như:
- Bài toán chuyển động
- Bài toán làm chung, làm riêng
- Bài toán dân số
- Bài toán về tỉ lệ, phần trăm
"""
    }
]


async def populate_mock_data():
    """Populate Milvus with mock educational documents."""
    logger.info("Starting mock data population...")
    
    content_agent = ContentProcessorAgent()
    processed_count = 0
    
    for doc_data in MOCK_DOCUMENTS:
        try:
            # Create document entity
            document = Document(
                id=uuid4(),
                title=doc_data["title"],
                subject=doc_data["subject"],
                grade=doc_data["grade"],
                document_type=DocumentType.READING_MATERIAL,
                file_path=f"/mock/{doc_data['title'].replace(' ', '_')}.txt",
                file_extension=".txt",
                file_size_bytes=len(doc_data["content"]),
                teacher_id=uuid4(),  # Mock teacher ID
                class_name="9A1",
                extracted_text=doc_data["content"],
                created_at=datetime.utcnow(),
            )
            
            logger.info(f"Processing: {document.title}")
            
            # Since we're working with direct text content (no actual file),
            # we'll manually process it instead of using process_document
            
            # Step 1: Chunk the text
            from utils.embeddings import chunk_text, generate_embeddings
            
            chunks = chunk_text(doc_data["content"], chunk_size=1000, overlap=200)
            logger.info(f"  Created {len(chunks)} text chunks")
            
            # Step 2: Generate embeddings
            embeddings = await generate_embeddings(chunks)
            logger.info(f"  Generated embeddings: type={type(embeddings)}, len={len(embeddings)}")
            
            # Debug: Check first embedding shape
            if embeddings and len(embeddings) > 0:
                logger.info(f"  First embedding type: {type(embeddings[0])}, shape: {len(embeddings[0]) if isinstance(embeddings[0], list) else 'N/A'}")
            
            # Validate lengths match
            if len(embeddings) != len(chunks):
                logger.error(f"  Length mismatch! chunks={len(chunks)}, embeddings={len(embeddings)}")
                logger.error(f"  This will cause Milvus insertion to fail")
                continue
            
            # Step 3: Store in Milvus
            milvus_ids = await content_agent.document_repo.store_embeddings(
                document=document,
                chunks=chunks,
                embeddings=embeddings,
            )
            logger.info(f"  Stored {len(milvus_ids)} vectors in Milvus")
            
            # Step 4: Mark as embedded
            document.mark_as_embedded(milvus_ids)
            
            if milvus_ids and len(milvus_ids) > 0:
                processed_count += 1
                logger.info(f"✓ Successfully added: {document.title}")
            else:
                logger.error(f"✗ Failed to store embeddings for: {document.title}")
                
        except Exception as e:
            logger.error(f"Error processing {doc_data['title']}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Mock data population complete!")
    logger.info(f"Successfully processed: {processed_count}/{len(MOCK_DOCUMENTS)} documents")
    logger.info(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(populate_mock_data())
