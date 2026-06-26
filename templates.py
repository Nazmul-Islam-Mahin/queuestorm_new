from typing import Dict, Any

# Templates mapped by (case_type, evidence_verdict)
TEMPLATES: Dict[str, Dict[str, Dict[str, str]]] = {
    "wrong_transfer": {
        "consistent": {
            "agent_summary": "Customer reports sending {amount} BDT via {txn_id} to {counterparty}, which they now believe was the wrong recipient.",
            "recommended_next_action": "Verify {txn_id} details with the customer and initiate the wrong-transfer dispute workflow per policy.",
            "customer_reply_en": "We have noted your concern about transaction {txn_id}. Please do not share your PIN or OTP with anyone. Our dispute team will review the case and contact you through official support channels.",
            "customer_reply_bn": "আপনার লেনদেন {txn_id} এর বিষয়ে আমরা অবগত হয়েছি। অনুগ্রহ করে কারো সাথে আপনার পিন বা ওটিপি শেয়ার করবেন না। আমাদের dispute টিম বিষয়টি খতিয়ে দেখে অফিসিয়াল চ্যানেলে আপনার সাথে যোগাযোগ করবে।"
        },
        "inconsistent": {
            "agent_summary": "Customer claims {txn_id} ({amount} BDT to {counterparty}) was a wrong transfer, but transaction history shows prior transfers to the same counterparty, suggesting an established recipient.",
            "recommended_next_action": "Flag for human review. Verify with the customer whether this was genuinely a wrong transfer given the established transaction pattern with this recipient.",
            "customer_reply_en": "We have received your request regarding transaction {txn_id}. Please do not share your PIN or OTP with anyone. Our dispute team will review the case carefully and contact you through official support channels.",
            "customer_reply_bn": "আমরা আপনার লেনদেন {txn_id} সংক্রান্ত অনুরোধটি পেয়েছি। অনুগ্রহ করে কারো সাথে আপনার পিন বা ওটিপি শেয়ার করবেন না। আমাদের dispute টিম বিষয়টি খতিয়ে দেখে অফিসিয়াল চ্যানেলে আপনার সাথে যোগাযোগ করবে।"
        },
        "insufficient_data": {
            "agent_summary": "Customer reports a wrong transfer issue but the transaction history does not contain clear matching evidence.",
            "recommended_next_action": "Reply to customer asking for clarification on the recipient's number, transaction ID, or correct transaction details.",
            "customer_reply_en": "Thank you for reaching out. We see multiple transactions or could not find a matching transfer. Could you share the recipient's number or transaction ID? Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "যোগাযোগ করার জন্য ধন্যবাদ। আমরা আপনার ভুল স্থানান্তরের অভিযোগের সাথে ম্যাচিং লেনদেন খুঁজে পাইনি। অনুগ্রহ করে প্রাপকের নম্বর বা লেনদেন আইডি শেয়ার করবেন কি? আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        }
    },
    "payment_failed": {
        "consistent": {
            "agent_summary": "Customer attempted a {amount} BDT payment ({txn_id}) which failed, but reports balance was deducted. Requires payments operations investigation.",
            "recommended_next_action": "Investigate {txn_id} ledger status. If balance was deducted on a failed payment, initiate the automatic reversal flow within standard SLA.",
            "customer_reply_en": "We have noted that transaction {txn_id} may have caused an unexpected balance deduction. Our payments team will review the case and any eligible amount will be returned through official channels. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "আমরা লক্ষ্য করেছি যে লেনদেন {txn_id} এর কারণে আপনার অ্যাকাউন্ট থেকে টাকা কেটে নেওয়া হয়ে থাকতে পারে। আমাদের পেমেন্ট টিম বিষয়টি পর্যালোচনা করবে এবং যেকোনো যোগ্য পরিমাণ অফিসিয়াল চ্যানেলের মাধ্যমে ফেরত দেওয়া হবে। অনুগ্রহ করে আপনার পিন বা ওটিপি শেয়ার করবেন না।"
        },
        "inconsistent": {
            "agent_summary": "Customer claims payment {txn_id} ({amount} BDT) failed and deducted, but transaction history shows it was completed successfully.",
            "recommended_next_action": "Verify with the merchant or biller if the payment was received. If yes, inform the customer the transaction was completed successfully.",
            "customer_reply_en": "We have checked transaction {txn_id} and it shows as successfully completed in our system. Please check with the recipient or merchant. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "আমরা {txn_id} লেনদেনটি চেক করেছি এবং এটি আমাদের সিস্টেমে সফলভাবে সম্পন্ন হয়েছে বলে দেখাচ্ছে। অনুগ্রহ করে মার্চেন্ট বা প্রাপকের সাথে যোগাযোগ করুন। আপনার পিন বা ওটিপি শেয়ার করবেন না।"
        },
        "insufficient_data": {
            "agent_summary": "Customer reports a failed payment, but no matching transaction was found in the provided history.",
            "recommended_next_action": "Ask the customer to share the transaction ID, amount, and merchant name.",
            "customer_reply_en": "Thank you for contacting us. We could not find the failed payment in your recent history. Please share the transaction ID and amount. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "যোগাযোগ করার জন্য ধন্যবাদ। আপনার সাম্প্রতিক ইতিহাসে এই ব্যর্থ পেমেন্টটি পাওয়া যায়নি। অনুগ্রহ করে ট্রানজেকশন আইডি এবং পরিমাণ শেয়ার করুন। আপনার পিন বা ওটিপি শেয়ার করবেন না।"
        }
    },
    "refund_request": {
        "consistent": {
            "agent_summary": "Customer requests refund of {amount} BDT for {txn_id} (merchant payment) due to change of mind. Not a service failure.",
            "recommended_next_action": "Inform the customer that refund eligibility depends on the merchant's own policy. Provide guidance on contacting the merchant directly for a refund.",
            "customer_reply_en": "Thank you for reaching out. Refunds for completed merchant payments depend on the merchant's own policy. We recommend contacting the merchant directly. If you need help reaching them, please reply and we will guide you. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "যোগাযোগ করার জন্য ধন্যবাদ। সম্পন্ন হওয়া মার্চেন্ট পেমেন্টের রিফান্ড মার্চেন্টের নিজস্ব পলিসির ওপর নির্ভর করে। আমরা সরাসরি মার্চেন্টের সাথে যোগাযোগ করার পরামর্শ দিচ্ছি। আপনার পিন বা ওটিপি শেয়ার করবেন না।"
        },
        "inconsistent": {
            "agent_summary": "Customer is requesting a refund for transaction {txn_id} but it is inconsistent with merchant policies or transaction state.",
            "recommended_next_action": "Review the transaction state and check merchant policy constraints. Refer the customer to the merchant.",
            "customer_reply_en": "Thank you for reaching out. Refunds depend on the merchant's own policy. We recommend contacting the merchant directly to resolve this. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "যোগাযোগ করার জন্য ধন্যবাদ। রিফান্ড মার্চেন্টের নিজস্ব পলিসির ওপর নির্ভর করে। আমরা মার্চেন্টের সাথে সরাসরি যোগাযোগ করার পরামর্শ দিচ্ছি। আপনার পিন বা ওটিপি শেয়ার করবেন না।"
        },
        "insufficient_data": {
            "agent_summary": "Customer is requesting a refund but no matching transaction was found in the provided history.",
            "recommended_next_action": "Ask the customer to provide the transaction ID and merchant details to verify the request.",
            "customer_reply_en": "Thank you for reaching out. We could not find a matching transaction in your history. Please share the transaction ID and merchant details. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "যোগাযোগ করার জন্য ধন্যবাদ। আমরা কোনো ম্যাচিং লেনদেন খুঁজে পাইনি। অনুগ্রহ করে লেনদেনের আইডি এবং মার্চেন্টের বিবরণ শেয়ার করুন। আপনার পিন বা ওটিপি শেয়ার করবেন না।"
        }
    },
    "duplicate_payment": {
        "consistent": {
            "agent_summary": "Customer reports duplicate payment. Two identical {amount} BDT payments to {counterparty} were completed close together ({txn_id} and prior transaction). The second ({txn_id}) is likely the duplicate.",
            "recommended_next_action": "Verify the duplicate with payments_ops. If the biller/merchant confirms only one payment was received, initiate reversal of {txn_id}.",
            "customer_reply_en": "We have noted the possible duplicate payment for transaction {txn_id}. Our payments team will verify with the biller and any eligible amount will be returned through official channels. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "আমরা {txn_id} লেনদেনের সম্ভাব্য ডুপ্লিকেট পেমেন্টটি লক্ষ্য করেছি। আমাদের পেমেন্ট টিম বিষয়টি যাচাই করবে এবং যেকোনো যোগ্য পরিমাণ অফিসিয়াল চ্যানেলের মাধ্যমে ফেরত দেওয়া হবে। আপনার পিন বা ওটিপি শেয়ার করবেন না।"
        },
        "inconsistent": {
            "agent_summary": "Customer claims duplicate payment for {txn_id}, but transaction history shows different counterparties or amounts, contradicting the duplicate claim.",
            "recommended_next_action": "Flag for human review. Ask the customer to clarify the duplicate transaction details.",
            "customer_reply_en": "Thank you for contacting us. We see differing transaction details in your recent history. Please share the transaction details for both deductions. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "যোগাযোগ করার জন্য ধন্যবাদ। আমরা আপনার ইতিহাসে আলাদা বিবরণসহ লেনদেন দেখতে পাচ্ছি। অনুগ্রহ করে উভয় লেনদেনের আইডি শেয়ার করুন। আপনার পিন বা ওটিপি শেয়ার করবেন না।"
        },
        "insufficient_data": {
            "agent_summary": "Customer claims duplicate payment, but transaction history does not show duplicate identical transactions.",
            "recommended_next_action": "Flag for human review. Ask the customer to provide the transaction IDs and details of both deductions.",
            "customer_reply_en": "Thank you for contacting us. We see only one transaction of this amount in your recent history. Please share both transaction IDs and details so we can investigate. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "যোগাযোগ করার জন্য ধন্যবাদ। আমরা আপনার ইতিহাসে শুধুমাত্র একটি লেনদেন দেখতে পাচ্ছি। অনুগ্রহ করে উভয় লেনদেনের আইডি শেয়ার করুন। আপনার পিন বা ওটিপি শেয়ার করবেন না।"
        }
    },
    "merchant_settlement_delay": {
        "consistent": {
            "agent_summary": "Merchant reports yesterday's {amount} BDT settlement ({txn_id}) is delayed beyond the standard next-day window. Settlement status is pending.",
            "recommended_next_action": "Route to merchant_operations to verify settlement batch status. If the batch is delayed, communicate a revised ETA to the merchant.",
            "customer_reply_en": "We have noted your concern about settlement {txn_id}. Our merchant operations team will check the batch status and update you on the expected settlement time through official channels.",
            "customer_reply_bn": "আমরা আপনার {txn_id} সেটেলমেন্ট সংক্রান্ত বিষয়টি গ্রহণ করেছি। আমাদের মার্চেন্ট অপারেশনস দল ব্যাচের স্থিতি পরীক্ষা করবে এবং অফিসিয়াল চ্যানেলের মাধ্যমে আপনাকে আপডেট করবে।"
        },
        "inconsistent": {
            "agent_summary": "Merchant reports settlement delay for {txn_id}, but history shows it is already completed.",
            "recommended_next_action": "Inform the merchant that the settlement was successfully completed. Provide batch reference details.",
            "customer_reply_en": "We have checked the settlement status for {txn_id} and it shows as successfully completed in our system. Please check your linked settlement account.",
            "customer_reply_bn": "আমরা আপনার {txn_id} সেটেলমেন্টের স্থিতি পরীক্ষা করেছি এবং এটি সফলভাবে সম্পন্ন হয়েছে বলে দেখাচ্ছে। অনুগ্রহ করে আপনার লিঙ্কড সেটেলমেন্ট অ্যাকাউন্টটি চেক করুন।"
        },
        "insufficient_data": {
            "agent_summary": "Merchant reports a settlement delay, but no matching pending settlement transaction was found.",
            "recommended_next_action": "Ask the merchant for the settlement date, batch ID, or amount to verify with finance.",
            "customer_reply_en": "Thank you for contacting merchant support. We could not find a matching pending settlement in your recent history. Please share the settlement date and amount. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "যোগাযোগ করার জন্য ধন্যবাদ। আমরা কোনো পেন্ডিং সেটেলমেন্ট খুঁজে পাইনি। অনুগ্রহ করে সেটেলমেন্টের তারিখ ও পরিমাণ শেয়ার করুন। আপনার পিন বা ওটিপি শেয়ার করবেন না।"
        }
    },
    "agent_cash_in_issue": {
        "consistent": {
            "agent_summary": "Customer reports {amount} BDT cash-in via {counterparty} ({txn_id}) not reflected in balance. Transaction status is pending. Agent claims funds were sent.",
            "recommended_next_action": "Investigate {txn_id} pending status with agent operations. Confirm settlement state and resolve within the standard cash-in SLA.",
            "customer_reply_en": "We have noted that your cash-in transaction {txn_id} is currently pending. Our agent operations team will verify the transaction status and it will be updated soon. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "আপনার লেনদেন {txn_id} এর বিষয়ে আমরা অবগত হয়েছি। আমাদের এজেন্ট অপারেশন্স দল এটি দ্রুত যাচাই করবে এবং অফিসিয়াল চ্যানেলে আপনাকে জানাবে। অনুগ্রহ করে কারো সাথে আপনার পিন বা ওটিপি শেয়ার করবেন না।"
        },
        "inconsistent": {
            "agent_summary": "Customer reports agent cash-in issue for {txn_id}, but history shows the cash-in was successfully completed.",
            "recommended_next_action": "Verify customer balance update. Inform customer the transaction shows completed and they should check their wallet balance.",
            "customer_reply_en": "We have verified transaction {txn_id} and it has been successfully completed. The amount has been credited to your balance. Please check your wallet. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "আমরা {txn_id} লেনদেনটি যাচাই করেছি এবং এটি সফলভাবে সম্পন্ন হয়েছে। আপনার ব্যালেন্সে টাকা যোগ করা হয়েছে। অনুগ্রহ করে ওয়ালেট ব্যালেন্স চেক করুন। পিন বা ওটিপি শেয়ার করবেন না।"
        },
        "insufficient_data": {
            "agent_summary": "Customer reports agent cash-in issue, but no matching transaction was found in history.",
            "recommended_next_action": "Ask the customer to provide the agent ID, transaction ID, and cash-in amount.",
            "customer_reply_en": "Thank you for reaching out. We could not find a matching cash-in transaction in your history. Please share the transaction ID and agent ID. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "যোগাযোগ করার জন্য ধন্যবাদ। আমরা কোনো ক্যাশ-ইন লেনদেন খুঁজে পাইনি। অনুগ্রহ করে লেনদেনের আইডি এবং এজেন্টের আইডি শেয়ার করুন। আপনার পিন বা ওটিপি শেয়ার করবেন না।"
        }
    },
    "phishing_or_social_engineering": {
        "consistent": {
            "agent_summary": "Customer reports an unsolicited call or message claiming to be from the company and asking for OTP/PIN. Customer safety needs reinforcement. Likely social engineering attempt.",
            "recommended_next_action": "Escalate to fraud_risk team immediately. Confirm to customer that the company never asks for OTP or PIN. Log the reported details for pattern analysis.",
            "customer_reply_en": "Thank you for reaching out before sharing any information. We never ask for your PIN, OTP, or password under any circumstances. Please do not share these with anyone, even if they claim to be from us. Our fraud team has been notified of this incident.",
            "customer_reply_bn": "কোনো তথ্য শেয়ার করার আগে আমাদের সাথে যোগাযোগ করার জন্য ধন্যবাদ। আমরা কোনো অবস্থাতেই আপনার পিন, ওটিপি বা পাসওয়ার্ড চাই না। অনুগ্রহ করে এগুলি কারো সাথে শেয়ার করবেন না। আমাদের ফ্রড টিমকে বিষয়টি অবহিত করা হয়েছে।"
        },
        "inconsistent": {
            "agent_summary": "Customer reports a phishing attempt, but transaction history indicates a pattern of normal usage.",
            "recommended_next_action": "Escalate to fraud_risk team immediately. Reassure the customer and log reported credentials.",
            "customer_reply_en": "Thank you for reaching out before sharing any information. We never ask for your PIN, OTP, or password under any circumstances. Please do not share these with anyone, even if they claim to be from us. Our fraud team has been notified of this incident.",
            "customer_reply_bn": "কোনো তথ্য শেয়ার করার আগে আমাদের সাথে যোগাযোগ করার জন্য ধন্যবাদ। আমরা কোনো অবস্থাতেই আপনার পিন, ওটিপি বা পাসওয়ার্ড চাই না। অনুগ্রহ করে এগুলি কারো সাথে শেয়ার করবেন না। আমাদের ফ্রড টিমকে বিষয়টি অবহিত করা হয়েছে।"
        },
        "insufficient_data": {
            "agent_summary": "Customer reports an unsolicited call claiming to be from the company and asking for OTP. Customer has not yet shared credentials. Likely social engineering attempt.",
            "recommended_next_action": "Escalate to fraud_risk team immediately. Confirm to customer that the company never asks for OTP. Log the reported number for fraud pattern analysis.",
            "customer_reply_en": "Thank you for reaching out before sharing any information. We never ask for your PIN, OTP, or password under any circumstances. Please do not share these with anyone, even if they claim to be from us. Our fraud team has been notified of this incident.",
            "customer_reply_bn": "কোনো তথ্য শেয়ার করার আগে আমাদের সাথে যোগাযোগ করার জন্য ধন্যবাদ। আমরা কোনো অবস্থাতেই আপনার পিন, ওটিপি বা পাসওয়ার্ড চাই না। অনুগ্রহ করে এগুলি কারো সাথে শেয়ার করবেন না। আমাদের ফ্রড টিমকে বিষয়টি অবহিত করা হয়েছে।"
        }
    },
    "other": {
        "consistent": {
            "agent_summary": "Customer reports a vague concern about their account or transaction without specifying transaction, amount, or issue.",
            "recommended_next_action": "Reply to customer asking for specific details: which transaction, what amount, what went wrong, and approximate time.",
            "customer_reply_en": "Thank you for reaching out. To help you faster, please share the transaction ID, the amount involved, and a short description of what went wrong. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "যোগাযোগ করার জন্য ধন্যবাদ। আপনাকে দ্রুত সাহায্য করতে অনুগ্রহ করে লেনদেনের আইডি, জড়িত পরিমাণ এবং কী সমস্যা হয়েছে তার সংক্ষিপ্ত বিবরণ শেয়ার করুন। আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        },
        "inconsistent": {
            "agent_summary": "Customer reports a concern that is inconsistent with their general transaction history pattern.",
            "recommended_next_action": "Ask customer for more details regarding their specific issue to verify further.",
            "customer_reply_en": "Thank you for reaching out. To help you faster, please share the transaction ID, the amount involved, and a short description of what went wrong. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "যোগাযোগ করার জন্য ধন্যবাদ। আপনাকে দ্রুত সাহায্য করতে অনুগ্রহ করে লেনদেনের আইডি, জড়িত পরিমাণ এবং কী সমস্যা হয়েছে তার সংক্ষিপ্ত বিবরণ শেয়ার করুন। আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        },
        "insufficient_data": {
            "agent_summary": "Customer reports a vague concern about their money without specifying transaction, amount, or issue. Insufficient detail to identify any relevant transaction.",
            "recommended_next_action": "Reply to customer asking for specific details: which transaction, what amount, what went wrong, and approximate time.",
            "customer_reply_en": "Thank you for reaching out. To help you faster, please share the transaction ID, the amount involved, and a short description of what went wrong. Please do not share your PIN or OTP with anyone.",
            "customer_reply_bn": "যোগাযোগ করার জন্য ধন্যবাদ। আপনাকে দ্রুত সাহায্য করতে অনুগ্রহ করে লেনদেনের আইডি, জড়িত পরিমাণ এবং কী সমস্যা হয়েছে তার সংক্ষিপ্ত বিবরণ শেয়ার করুন। আপনার পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        }
    }
}

def get_filled_templates(
    case_type: str,
    verdict: str,
    txn_id: str,
    amount: str,
    counterparty: str,
    is_bangla: bool = False
) -> Dict[str, str]:
    """
    Returns filled agent summary, next action, and customer reply based on inputs.
    """
    # Safeguard case_type and verdict inputs
    if case_type not in TEMPLATES:
        case_type = "other"
    if verdict not in TEMPLATES[case_type]:
        verdict = "insufficient_data"
        
    case_dict = TEMPLATES[case_type][verdict]
    
    # Setup placeholder formatting dict
    fmt_txn = txn_id if txn_id else "transaction"
    fmt_amt = amount if amount else "money"
    fmt_cp = counterparty if counterparty else "recipient"
    
    fmt_kwargs = {
        "txn_id": fmt_txn,
        "amount": fmt_amt,
        "counterparty": fmt_cp
    }
    
    # Select customer reply language
    reply_key = "customer_reply_bn" if is_bangla else "customer_reply_en"
    
    return {
        "agent_summary": case_dict["agent_summary"].format(**fmt_kwargs),
        "recommended_next_action": case_dict["recommended_next_action"].format(**fmt_kwargs),
        "customer_reply": case_dict[reply_key].format(**fmt_kwargs)
    }
