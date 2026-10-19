package com.invoiceintake.validator;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/** Business rules applied to extracted invoice data. Pure logic, no AWS types, so it is easy to test. */
public class InvoiceValidator {

    private static final Pattern GSTIN = Pattern.compile("^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$");
    private static final BigDecimal TOLERANCE = new BigDecimal("0.01");

    private final java.time.Clock clock;

    public InvoiceValidator() {
        this(java.time.Clock.systemDefaultZone());
    }

    public InvoiceValidator(java.time.Clock clock) {
        this.clock = clock;
    }

    /** Returns a list of problems; an empty list means the invoice is valid. */
    public List<String> validate(InvoiceData d) {
        List<String> errors = new ArrayList<>();
        if (d == null) {
            errors.add("body is empty");
            return errors;
        }
        if (isBlank(d.vendor)) errors.add("vendor is required");
        if (isBlank(d.invoiceNumber)) errors.add("invoiceNumber is required");

        if (isBlank(d.invoiceDate)) {
            errors.add("invoiceDate is required");
        } else {
            try {
                if (LocalDate.parse(d.invoiceDate).isAfter(LocalDate.now(clock))) {
                    errors.add("invoiceDate is in the future");
                }
            } catch (DateTimeParseException e) {
                errors.add("invoiceDate must be yyyy-MM-dd");
            }
        }

        if (d.subtotal == null || d.subtotal.signum() < 0) errors.add("subtotal must be zero or more");
        if (d.taxAmount == null || d.taxAmount.signum() < 0) errors.add("taxAmount must be zero or more");
        if (d.total == null || d.total.signum() <= 0) errors.add("total must be greater than zero");

        if (d.subtotal != null && d.taxAmount != null && d.total != null
                && d.subtotal.signum() >= 0 && d.taxAmount.signum() >= 0 && d.total.signum() > 0) {
            BigDecimal diff = d.subtotal.add(d.taxAmount).subtract(d.total).abs();
            if (diff.compareTo(TOLERANCE) > 0) {
                errors.add("total must equal subtotal + taxAmount");
            }
        }

        if (!isBlank(d.gstin) && !GSTIN.matcher(d.gstin.trim().toUpperCase()).matches()) {
            errors.add("gstin is not a valid 15-character GSTIN");
        }
        return errors;
    }

    /** Trim text fields and apply defaults. Call only after validate() returned no errors. */
    public InvoiceData normalize(InvoiceData d) {
        d.vendor = d.vendor.trim();
        d.invoiceNumber = d.invoiceNumber.trim();
        d.gstin = isBlank(d.gstin) ? null : d.gstin.trim().toUpperCase();
        d.currency = isBlank(d.currency) ? "INR" : d.currency.trim().toUpperCase();
        return d;
    }

    private static boolean isBlank(String s) {
        return s == null || s.trim().isEmpty();
    }
}
