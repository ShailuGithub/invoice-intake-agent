package com.invoiceintake.validator;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

import java.math.BigDecimal;

/** Fields extracted from an invoice by the Python service. */
@JsonIgnoreProperties(ignoreUnknown = true)
public class InvoiceData {
    public String vendor;
    public String invoiceNumber;
    public String invoiceDate;   // yyyy-MM-dd
    public BigDecimal subtotal;
    public BigDecimal taxAmount;
    public BigDecimal total;
    public String gstin;         // optional, 15 chars
    public String currency;      // optional, defaults to INR
}
