# FMCG portfolio demo: 5–7 minutes

เปิด `output/index.html` หลังแตก ZIP ไม่ต้องเปิด server หรือฐานข้อมูลเพื่อดู Demo ที่รวมไว้ หากรัน report ใหม่ ให้สร้างหน้ารวมอีกครั้งด้วย `python3 scripts/build_demo.py`.

## 1. ปัญหาที่ระบบตอบ

“โปรเจกต์นี้เชื่อมยอดขายส่ง ยอดขายปลีก สต็อก และคำสั่งซื้อ เพื่อดูผลงานเทียบเป้า พยากรณ์ปิดปี และประเมินโปรโมชันกับความเสี่ยงสินค้าไม่พอขาย ผมสร้างข้อมูลจำลองทั้งหมด เพื่อให้ตรวจคำตอบของวิธีวิเคราะห์ได้โดยไม่ใช้ไฟล์ธุรกิจจริง”

## 2. แหล่งตัวเลขและการตรวจข้อมูล

Config และ seed → simulation รายวัน → warehouse CSV กับข้อมูลคำตอบจำลองที่แยกไว้ → manifest และ DQ gate → KPI / forecast / estimators → offline dashboard. PostgreSQL DDL/COPY loader มีไว้แล้ว แต่ผล DB acceptance ต้องยืนยันจากการรันจริงแยกต่างหาก.

อธิบายจุดตรวจสำคัญ: ราคากับยอดเงินเป็นสตางค์, จำนวนส่งของต้องตรงกับสินค้าเข้าสต็อก, สินค้าขายออกตรงกับ stock ledger, ไม่มี actual อนาคตเข้าตัวประมาณ. ข้อมูลที่รู้คำตอบใช้เฉพาะตรวจวิธี ไม่ใช้เป็น input ฝึก/ประมาณผล.

## 3. M2: Commercial & service

เลือกห้างและหมวดสินค้า แสดง SI/SO, %Contribution, growth, target attainment และ OTIF. อธิบาย denominator ของแต่ละ KPI และเหตุผลที่ order OTIF ไม่จำเป็นต้องต่ำกว่า line OTIF เพราะหน่วยถ่วงน้ำหนักต่างกัน.

## 4. M3: วิธีเดียวสำหรับ baseline

แสดง WAPE สอง historical origins และกฎเลือกวิธีที่ต้องชนะ seasonal naive ทั้งสองช่วง. วิธีที่ได้คือ LY × YTD growth. Gap รวม 484,653.13 บาทเป็นผลจาก actual YTD + Q4 forecast เทียบ annual target ไม่ใช่ตัวเลขปรับให้ถึงเป้า. C02 เป็นห้างที่ต้องตรวจแผนปิด Gap ก่อน.

## 5. M4: ไม่ดูเฉพาะยอดเพิ่มช่วงโปรโมชัน

แสดง gross uplift, post-promo dip และ net uplift รวม stockout cohort. B1 ประมาณได้ 240 โปรโมชัน แต่ B2 ไม่มี clean control ใน calendar ชุดนี้ จึงไม่แสดงค่าที่แต่งขึ้น. ผล SO uplift ยังไม่คูณเข้า SI forecast โดยตรง เพราะต้องมี future promotion plan กับนโยบายเติมสต็อก และระวังนับผลโปรโมชันเดิมซ้ำกับ baseline.

## 6. M5: ความแม่นยำพร้อมข้อจำกัด

แสดง Days of Cover, availability และ latest risk. Held-out matched precision 6.24%, recall 92.30% หมายถึงจับเหตุการณ์ได้มากแต่แจ้งเตือนเกินมาก เพราะกฎยังไม่รวมสินค้าเข้าในอนาคต. เป็นจุดเริ่มต้นสำหรับคัดรายการไปตรวจ ไม่ใช่ automatic ordering. เปรียบเทียบกับ naive บนแถวเดียวกันและแสดง coverage. Latest วันที่ 30 ก.ย. ไม่มี future label ครบ จึงไม่รวมในผลประเมิน.

## 7. สิ่งที่ทำต่อได้อย่างตรวจสอบได้

รัน DB acceptance เพื่อยืนยัน load/rollback/parity; สร้าง calendar แยกสำหรับทดสอบ B2; กันช่วงประเมินใหม่สำหรับ receipt-aware risk; ทำ Q4 SI scenario ผ่าน stock/replenishment bridge. อย่าอ้าง real-world forecast accuracy หรือ production deployment จากผลจำลองนี้.

รายละเอียดสูตรและข้อจำกัดอยู่ใน M2–M5 acceptance documents; ดู log/summary เพื่อแยกสิ่งที่ผ่านจริงออกจากสิ่งที่ยังข้าม.
