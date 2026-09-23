"""
Email templates for all notification types (ar/fr/en).
Each template is HTML with Jinja2-style {{ variableName }} placeholders.

7 notification types × 3 locales = 21 templates.
"""
from __future__ import annotations

# ─── Arabic Templates ─────────────────────────────────────────────────────────

TEMPLATE_ENROLLMENT_APPROVED_AR = """\
<html dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
    <div style="background:#2563eb;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:20px;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#1e40af;margin-top:0;">✅ تم قبول تسجيلك</h2>
      <p>مرحباً <strong>{{ firstName }}</strong>،</p>
      <p>يسرنا إخبارك بأنه تم قبول طلب تسجيلك في:</p>
      <div style="background:#eff6ff;border-right:4px solid #2563eb;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>الفصل:</strong> {{ className }}</p>
        <p style="margin:4px 0;"><strong>المجموعة:</strong> {{ groupName }}</p>
        <p style="margin:4px 0;"><strong>الجدول:</strong> {{ schedule }}</p>
        <p style="margin:4px 0;"><strong>السعر:</strong> {{ price }} دج</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#2563eb;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">
          الذهاب إلى لوحة التحكم
        </a>
      </div>
      <p style="color:#6b7280;font-size:14px;">شكراً لاختيارك {{ schoolName }}.</p>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_ENROLLMENT_REJECTED_AR = """\
<html dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
    <div style="background:#dc2626;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:20px;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#dc2626;margin-top:0;">❌ لم يتم قبول طلب التسجيل</h2>
      <p>مرحباً <strong>{{ firstName }}</strong>،</p>
      <p>نأسف لإعلامك أنه لم يتم قبول طلب تسجيلك في <strong>{{ className }}</strong>.</p>
      {% if reason %}<p><strong>السبب:</strong> {{ reason }}</p>{% endif %}
      <p>يمكنك الاطلاع على الفصول الأخرى المتاحة والتسجيل في أي منها.</p>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ catalogLink }}" style="background:#2563eb;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">
          عرض الفصول المتاحة
        </a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_SUBSCRIPTION_EXPIRING_AR = """\
<html dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
    <div style="background:#ea580c;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:20px;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#ea580c;margin-top:0;">⚠️ اشتراكك ينتهي قريباً</h2>
      <p>مرحباً <strong>{{ firstName }}</strong>،</p>
      <p>نودّ تذكيرك بأن اشتراكك في <strong>{{ className }}</strong> سينتهي قريباً.</p>
      <div style="background:#fff7ed;border-right:4px solid #ea580c;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>تاريخ الانتهاء:</strong> {{ expiryDate }}</p>
        {% if remainingSessions is not none %}<p style="margin:4px 0;"><strong>الجلسات المتبقية:</strong> {{ remainingSessions }}</p>{% endif %}
      </div>
      <p>جدّد اشتراكك الآن لتتمكن من الاستمرار دون انقطاع.</p>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#ea580c;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">
          تجديد الاشتراك
        </a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_SUBSCRIPTION_EXPIRED_AR = """\
<html dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
    <div style="background:#dc2626;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:20px;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#dc2626;margin-top:0;">🔴 انتهى اشتراكك</h2>
      <p>مرحباً <strong>{{ firstName }}</strong>،</p>
      <p>انتهى اشتراكك في <strong>{{ className }}</strong> بتاريخ <strong>{{ expiryDate }}</strong>.</p>
      <p>للعودة إلى الفصل، يرجى تجديد اشتراكك في أقرب وقت.</p>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#dc2626;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">
          تجديد الآن
        </a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_PAYMENT_CONFIRMED_AR = """\
<html dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
    <div style="background:#16a34a;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:20px;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#16a34a;margin-top:0;">✅ تم تأكيد الدفع</h2>
      <p>مرحباً <strong>{{ firstName }}</strong>،</p>
      <p>تم استلام دفعتك بنجاح وتفعيل اشتراكك.</p>
      <div style="background:#f0fdf4;border-right:4px solid #16a34a;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>المبلغ:</strong> {{ amount }} دج</p>
        <p style="margin:4px 0;"><strong>طريقة الدفع:</strong> {{ method }}</p>
        <p style="margin:4px 0;"><strong>تاريخ الدفع:</strong> {{ paymentDate }}</p>
        <p style="margin:4px 0;"><strong>الفصل:</strong> {{ className }}</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#16a34a;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">
          عرض الاشتراكات
        </a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_ASSIGNMENT_SUBMITTED_AR = """\
<html dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
    <div style="background:#7c3aed;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:20px;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#7c3aed;margin-top:0;">📝 تم تسليم واجب جديد</h2>
      <p>مرحباً <strong>{{ teacherName }}</strong>،</p>
      <p>قام الطالب <strong>{{ studentName }}</strong> بتسليم الواجب التالي:</p>
      <div style="background:#f5f3ff;border-right:4px solid #7c3aed;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>الواجب:</strong> {{ assignmentTitle }}</p>
        <p style="margin:4px 0;"><strong>الفصل:</strong> {{ className }}</p>
        <p style="margin:4px 0;"><strong>تاريخ التسليم:</strong> {{ submissionDate }}</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#7c3aed;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">
          مراجعة التسليم
        </a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_ENROLLMENT_GROUP_TRANSFERRED_AR = """\
<html dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
    <div style="background:#0891b2;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:20px;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#0891b2;margin-top:0;">🔄 تم نقل تسجيلك</h2>
      <p>مرحباً <strong>{{ firstName }}</strong>،</p>
      <p>تم نقل تسجيلك إلى مجموعة جديدة.</p>
      <div style="background:#ecfeff;border-right:4px solid #0891b2;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>من المجموعة:</strong> {{ sourceGroupName }}</p>
        <p style="margin:4px 0;"><strong>إلى المجموعة:</strong> {{ targetGroupName }}</p>
        <p style="margin:4px 0;"><strong>الجدول الجديد:</strong> {{ newSchedule }}</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#0891b2;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">
          عرض تسجيلاتي
        </a>
      </div>
    </div>
  </div>
</body>
</html>"""

# ─── English Templates ────────────────────────────────────────────────────────

TEMPLATE_ENROLLMENT_APPROVED_EN = """\
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
    <div style="background:#2563eb;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:20px;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#1e40af;margin-top:0;">✅ Enrollment Approved</h2>
      <p>Hello <strong>{{ firstName }}</strong>,</p>
      <p>Your enrollment has been approved for:</p>
      <div style="background:#eff6ff;border-left:4px solid #2563eb;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>Class:</strong> {{ className }}</p>
        <p style="margin:4px 0;"><strong>Group:</strong> {{ groupName }}</p>
        <p style="margin:4px 0;"><strong>Schedule:</strong> {{ schedule }}</p>
        <p style="margin:4px 0;"><strong>Price:</strong> {{ price }} DA</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#2563eb;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">Go to Dashboard</a>
      </div>
      <p style="color:#6b7280;font-size:14px;">Thank you for choosing {{ schoolName }}.</p>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_ENROLLMENT_REJECTED_EN = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#dc2626;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#dc2626;margin-top:0;">❌ Enrollment Not Approved</h2>
      <p>Hello <strong>{{ firstName }}</strong>,</p>
      <p>Unfortunately, your enrollment request for <strong>{{ className }}</strong> was not approved.</p>
      {% if reason %}<p><strong>Reason:</strong> {{ reason }}</p>{% endif %}
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ catalogLink }}" style="background:#2563eb;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">Browse Other Classes</a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_SUBSCRIPTION_EXPIRING_EN = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#ea580c;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#ea580c;margin-top:0;">⚠️ Subscription Expiring Soon</h2>
      <p>Hello <strong>{{ firstName }}</strong>,</p>
      <p>Your subscription to <strong>{{ className }}</strong> is expiring soon.</p>
      <div style="background:#fff7ed;border-left:4px solid #ea580c;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>Expiry Date:</strong> {{ expiryDate }}</p>
        {% if remainingSessions is not none %}<p style="margin:4px 0;"><strong>Remaining Sessions:</strong> {{ remainingSessions }}</p>{% endif %}
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#ea580c;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">Renew Now</a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_SUBSCRIPTION_EXPIRED_EN = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#dc2626;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#dc2626;margin-top:0;">🔴 Subscription Expired</h2>
      <p>Hello <strong>{{ firstName }}</strong>,</p>
      <p>Your subscription to <strong>{{ className }}</strong> expired on <strong>{{ expiryDate }}</strong>.</p>
      <p>Renew now to continue attending sessions.</p>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#dc2626;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">Renew Now</a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_PAYMENT_CONFIRMED_EN = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#16a34a;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#16a34a;margin-top:0;">✅ Payment Confirmed</h2>
      <p>Hello <strong>{{ firstName }}</strong>,</p>
      <p>Your payment has been received and your subscription is active.</p>
      <div style="background:#f0fdf4;border-left:4px solid #16a34a;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>Amount:</strong> {{ amount }} DA</p>
        <p style="margin:4px 0;"><strong>Method:</strong> {{ method }}</p>
        <p style="margin:4px 0;"><strong>Date:</strong> {{ paymentDate }}</p>
        <p style="margin:4px 0;"><strong>Class:</strong> {{ className }}</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#16a34a;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">View Subscriptions</a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_ASSIGNMENT_SUBMITTED_EN = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#7c3aed;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#7c3aed;margin-top:0;">📝 Assignment Submitted</h2>
      <p>Hello <strong>{{ teacherName }}</strong>,</p>
      <p><strong>{{ studentName }}</strong> has submitted the following assignment:</p>
      <div style="background:#f5f3ff;border-left:4px solid #7c3aed;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>Assignment:</strong> {{ assignmentTitle }}</p>
        <p style="margin:4px 0;"><strong>Class:</strong> {{ className }}</p>
        <p style="margin:4px 0;"><strong>Submitted:</strong> {{ submissionDate }}</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#7c3aed;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">Review Submission</a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_ENROLLMENT_GROUP_TRANSFERRED_EN = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#0891b2;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#0891b2;margin-top:0;">🔄 Enrollment Transferred</h2>
      <p>Hello <strong>{{ firstName }}</strong>,</p>
      <p>Your enrollment has been moved to a new group.</p>
      <div style="background:#ecfeff;border-left:4px solid #0891b2;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>From:</strong> {{ sourceGroupName }}</p>
        <p style="margin:4px 0;"><strong>To:</strong> {{ targetGroupName }}</p>
        <p style="margin:4px 0;"><strong>New Schedule:</strong> {{ newSchedule }}</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#0891b2;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">View My Enrollments</a>
      </div>
    </div>
  </div>
</body>
</html>"""

# ─── French Templates ─────────────────────────────────────────────────────────

TEMPLATE_ENROLLMENT_APPROVED_FR = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#2563eb;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#1e40af;margin-top:0;">✅ Inscription approuvée</h2>
      <p>Bonjour <strong>{{ firstName }}</strong>,</p>
      <p>Votre inscription a été approuvée pour :</p>
      <div style="background:#eff6ff;border-left:4px solid #2563eb;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>Classe :</strong> {{ className }}</p>
        <p style="margin:4px 0;"><strong>Groupe :</strong> {{ groupName }}</p>
        <p style="margin:4px 0;"><strong>Horaire :</strong> {{ schedule }}</p>
        <p style="margin:4px 0;"><strong>Tarif :</strong> {{ price }} DA</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#2563eb;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">Accéder au tableau de bord</a>
      </div>
      <p style="color:#6b7280;font-size:14px;">Merci de faire confiance à {{ schoolName }}.</p>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_ENROLLMENT_REJECTED_FR = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#dc2626;padding:24px;text-align:center;"><h1 style="color:#fff;margin:0;">{{ schoolName }}</h1></div>
    <div style="padding:32px;">
      <h2 style="color:#dc2626;margin-top:0;">❌ Inscription non approuvée</h2>
      <p>Bonjour <strong>{{ firstName }}</strong>,</p>
      <p>Votre demande d'inscription à <strong>{{ className }}</strong> n'a pas été approuvée.</p>
      {% if reason %}<p><strong>Motif :</strong> {{ reason }}</p>{% endif %}
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ catalogLink }}" style="background:#2563eb;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">Voir les autres classes</a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_SUBSCRIPTION_EXPIRING_FR = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#ea580c;padding:24px;text-align:center;"><h1 style="color:#fff;margin:0;">{{ schoolName }}</h1></div>
    <div style="padding:32px;">
      <h2 style="color:#ea580c;margin-top:0;">⚠️ Abonnement expirant bientôt</h2>
      <p>Bonjour <strong>{{ firstName }}</strong>,</p>
      <p>Votre abonnement à <strong>{{ className }}</strong> expire bientôt.</p>
      <div style="background:#fff7ed;border-left:4px solid #ea580c;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>Date d'expiration :</strong> {{ expiryDate }}</p>
        {% if remainingSessions is not none %}<p style="margin:4px 0;"><strong>Séances restantes :</strong> {{ remainingSessions }}</p>{% endif %}
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#ea580c;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">Renouveler maintenant</a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_SUBSCRIPTION_EXPIRED_FR = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#dc2626;padding:24px;text-align:center;"><h1 style="color:#fff;margin:0;">{{ schoolName }}</h1></div>
    <div style="padding:32px;">
      <h2 style="color:#dc2626;margin-top:0;">🔴 Abonnement expiré</h2>
      <p>Bonjour <strong>{{ firstName }}</strong>,</p>
      <p>Votre abonnement à <strong>{{ className }}</strong> a expiré le <strong>{{ expiryDate }}</strong>.</p>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#dc2626;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">Renouveler</a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_PAYMENT_CONFIRMED_FR = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#16a34a;padding:24px;text-align:center;"><h1 style="color:#fff;margin:0;">{{ schoolName }}</h1></div>
    <div style="padding:32px;">
      <h2 style="color:#16a34a;margin-top:0;">✅ Paiement confirmé</h2>
      <p>Bonjour <strong>{{ firstName }}</strong>,</p>
      <p>Votre paiement a été reçu et votre abonnement est actif.</p>
      <div style="background:#f0fdf4;border-left:4px solid #16a34a;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>Montant :</strong> {{ amount }} DA</p>
        <p style="margin:4px 0;"><strong>Méthode :</strong> {{ method }}</p>
        <p style="margin:4px 0;"><strong>Date :</strong> {{ paymentDate }}</p>
        <p style="margin:4px 0;"><strong>Classe :</strong> {{ className }}</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#16a34a;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">Voir les abonnements</a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_ASSIGNMENT_SUBMITTED_FR = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#7c3aed;padding:24px;text-align:center;"><h1 style="color:#fff;margin:0;">{{ schoolName }}</h1></div>
    <div style="padding:32px;">
      <h2 style="color:#7c3aed;margin-top:0;">📝 Devoir soumis</h2>
      <p>Bonjour <strong>{{ teacherName }}</strong>,</p>
      <p><strong>{{ studentName }}</strong> a soumis le devoir suivant :</p>
      <div style="background:#f5f3ff;border-left:4px solid #7c3aed;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>Devoir :</strong> {{ assignmentTitle }}</p>
        <p style="margin:4px 0;"><strong>Classe :</strong> {{ className }}</p>
        <p style="margin:4px 0;"><strong>Soumis le :</strong> {{ submissionDate }}</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#7c3aed;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">Voir la soumission</a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_ENROLLMENT_GROUP_TRANSFERRED_FR = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#0891b2;padding:24px;text-align:center;"><h1 style="color:#fff;margin:0;">{{ schoolName }}</h1></div>
    <div style="padding:32px;">
      <h2 style="color:#0891b2;margin-top:0;">🔄 Inscription transférée</h2>
      <p>Bonjour <strong>{{ firstName }}</strong>,</p>
      <p>Votre inscription a été transférée vers un nouveau groupe.</p>
      <div style="background:#ecfeff;border-left:4px solid #0891b2;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>De :</strong> {{ sourceGroupName }}</p>
        <p style="margin:4px 0;"><strong>Vers :</strong> {{ targetGroupName }}</p>
        <p style="margin:4px 0;"><strong>Nouvel horaire :</strong> {{ newSchedule }}</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#0891b2;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">Voir mes inscriptions</a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_ASSIGNMENT_DUE_SOON_AR = """\
<html dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
    <div style="background:#d97706;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:20px;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#d97706;margin-top:0;">⏰ تذكير: اقتراب موعد تسليم الواجب</h2>
      <p>مرحباً <strong>{{ firstName }}</strong>،</p>
      <p>نودّ تذكيرك بأن موعد تسليم الواجب التالي يقترب:</p>
      <div style="background:#fffbeb;border-right:4px solid #d97706;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>الواجب:</strong> {{ assignmentTitle }}</p>
        <p style="margin:4px 0;"><strong>الفصل:</strong> {{ className }}</p>
        <p style="margin:4px 0;"><strong>تاريخ الاستحقاق:</strong> {{ dueDate }}</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#d97706;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">
          تسليم الواجب
        </a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_ASSIGNMENT_DUE_SOON_EN = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#d97706;padding:24px;text-align:center;">
      <h1 style="color:#fff;margin:0;">{{ schoolName }}</h1>
    </div>
    <div style="padding:32px;">
      <h2 style="color:#d97706;margin-top:0;">⏰ Reminder: Assignment Due Soon</h2>
      <p>Hello <strong>{{ firstName }}</strong>,</p>
      <p>This is a reminder that the following assignment is due soon:</p>
      <div style="background:#fffbeb;border-left:4px solid #d97706;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>Assignment:</strong> {{ assignmentTitle }}</p>
        <p style="margin:4px 0;"><strong>Class:</strong> {{ className }}</p>
        <p style="margin:4px 0;"><strong>Due Date:</strong> {{ dueDate }}</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#d97706;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">Submit Assignment</a>
      </div>
    </div>
  </div>
</body>
</html>"""

TEMPLATE_ASSIGNMENT_DUE_SOON_FR = """\
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:600px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;">
    <div style="background:#d97706;padding:24px;text-align:center;"><h1 style="color:#fff;margin:0;">{{ schoolName }}</h1></div>
    <div style="padding:32px;">
      <h2 style="color:#d97706;margin-top:0;">⏰ Rappel : Devoir à rendre bientôt</h2>
      <p>Bonjour <strong>{{ firstName }}</strong>,</p>
      <p>Nous vous rappelons que le devoir suivant doit être rendu bientôt :</p>
      <div style="background:#fffbeb;border-left:4px solid #d97706;padding:16px;border-radius:4px;margin:16px 0;">
        <p style="margin:4px 0;"><strong>Devoir :</strong> {{ assignmentTitle }}</p>
        <p style="margin:4px 0;"><strong>Classe :</strong> {{ className }}</p>
        <p style="margin:4px 0;"><strong>Date limite :</strong> {{ dueDate }}</p>
      </div>
      <div style="text-align:center;margin:24px 0;">
        <a href="{{ dashboardLink }}" style="background:#d97706;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-weight:bold;display:inline-block;">Soumettre le devoir</a>
      </div>
    </div>
  </div>
</body>
</html>"""

# ─── Template Registry ────────────────────────────────────────────────────────

TEMPLATES: dict[str, dict[str, str]] = {
    "enrollment_approved": {
        "ar": TEMPLATE_ENROLLMENT_APPROVED_AR,
        "en": TEMPLATE_ENROLLMENT_APPROVED_EN,
        "fr": TEMPLATE_ENROLLMENT_APPROVED_FR,
    },
    "enrollment_rejected": {
        "ar": TEMPLATE_ENROLLMENT_REJECTED_AR,
        "en": TEMPLATE_ENROLLMENT_REJECTED_EN,
        "fr": TEMPLATE_ENROLLMENT_REJECTED_FR,
    },
    "subscription_expiring": {
        "ar": TEMPLATE_SUBSCRIPTION_EXPIRING_AR,
        "en": TEMPLATE_SUBSCRIPTION_EXPIRING_EN,
        "fr": TEMPLATE_SUBSCRIPTION_EXPIRING_FR,
    },
    "subscription_expired": {
        "ar": TEMPLATE_SUBSCRIPTION_EXPIRED_AR,
        "en": TEMPLATE_SUBSCRIPTION_EXPIRED_EN,
        "fr": TEMPLATE_SUBSCRIPTION_EXPIRED_FR,
    },
    "payment_confirmed": {
        "ar": TEMPLATE_PAYMENT_CONFIRMED_AR,
        "en": TEMPLATE_PAYMENT_CONFIRMED_EN,
        "fr": TEMPLATE_PAYMENT_CONFIRMED_FR,
    },
    "assignment_submitted": {
        "ar": TEMPLATE_ASSIGNMENT_SUBMITTED_AR,
        "en": TEMPLATE_ASSIGNMENT_SUBMITTED_EN,
        "fr": TEMPLATE_ASSIGNMENT_SUBMITTED_FR,
    },
    "assignment_due_soon": {
        "ar": TEMPLATE_ASSIGNMENT_DUE_SOON_AR,
        "en": TEMPLATE_ASSIGNMENT_DUE_SOON_EN,
        "fr": TEMPLATE_ASSIGNMENT_DUE_SOON_FR,
    },
    "enrollment_group_transferred": {
        "ar": TEMPLATE_ENROLLMENT_GROUP_TRANSFERRED_AR,
        "en": TEMPLATE_ENROLLMENT_GROUP_TRANSFERRED_EN,
        "fr": TEMPLATE_ENROLLMENT_GROUP_TRANSFERRED_FR,
    },
}


def get_email_template(notification_type: str, locale: str = "ar") -> str | None:
    """
    Retrieve an HTML template by notification type and locale.
    Falls back to Arabic if the requested locale is not available.
    Returns None if the notification type has no template registered.
    """
    type_templates = TEMPLATES.get(notification_type)
    if not type_templates:
        return None
    return type_templates.get(locale) or type_templates.get("ar")
