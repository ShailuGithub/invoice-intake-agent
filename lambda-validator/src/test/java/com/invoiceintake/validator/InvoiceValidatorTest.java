package com.invoiceintake.validator;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class InvoiceValidatorTest {

    private final InvoiceValidator validator =
            new InvoiceValidator(Clock.fixed(Instant.parse("2026-10-19T00:00:00Z"), ZoneOffset.UTC));

    private InvoiceData valid() {
        InvoiceData d = new InvoiceData();
        d.vendor = "Sri Lakshmi Traders";
        d.invoiceNumber = "INV-1042";
        d.invoiceDate = "2026-10-01";
        d.subtotal = new BigDecimal("1000.00");
        d.taxAmount = new BigDecimal("180.00");
        d.total = new BigDecimal("1180.00");
        d.gstin = "29ABCDE1234F1Z5";
        return d;
    }

    @Test
    void validInvoicePasses() {
        assertTrue(validator.validate(valid()).isEmpty());
    }

    @Test
    void totalMustMatchSubtotalPlusTax() {
        InvoiceData d = valid();
        d.total = new BigDecimal("1200.00");
        assertTrue(validator.validate(d).contains("total must equal subtotal + taxAmount"));
    }

    @Test
    void roundingWithinOnePaiseIsAccepted() {
        InvoiceData d = valid();
        d.total = new BigDecimal("1180.01");
        assertTrue(validator.validate(d).isEmpty());
    }

    @Test
    void futureDateRejected() {
        InvoiceData d = valid();
        d.invoiceDate = "2026-12-01";
        assertTrue(validator.validate(d).contains("invoiceDate is in the future"));
    }

    @Test
    void badDateFormatRejected() {
        InvoiceData d = valid();
        d.invoiceDate = "01/10/2026";
        assertTrue(validator.validate(d).contains("invoiceDate must be yyyy-MM-dd"));
    }

    @Test
    void invalidGstinRejectedButMissingGstinAllowed() {
        InvoiceData d = valid();
        d.gstin = "NOTAGSTIN";
        assertTrue(validator.validate(d).contains("gstin is not a valid 15-character GSTIN"));
        d.gstin = null;
        assertTrue(validator.validate(d).isEmpty());
    }

    @Test
    void missingRequiredFieldsAreAllReported() {
        List<String> errors = validator.validate(new InvoiceData());
        assertTrue(errors.contains("vendor is required"));
        assertTrue(errors.contains("invoiceNumber is required"));
        assertTrue(errors.contains("invoiceDate is required"));
        assertTrue(errors.contains("total must be greater than zero"));
    }

    @Test
    void normalizeDefaultsCurrencyAndUppercasesGstin() {
        InvoiceData d = valid();
        d.vendor = "  Sri Lakshmi Traders ";
        d.gstin = "29abcde1234f1z5";
        InvoiceData n = validator.normalize(d);
        assertEquals("Sri Lakshmi Traders", n.vendor);
        assertEquals("29ABCDE1234F1Z5", n.gstin);
        assertEquals("INR", n.currency);
    }
}
