package com.invoiceintake.validator;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;

import static org.junit.jupiter.api.Assertions.*;

class HandlerTest {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private final Handler handler =
            new Handler(new InvoiceValidator(Clock.fixed(Instant.parse("2026-10-19T00:00:00Z"), ZoneOffset.UTC)));

    private JsonNode event(String bodyJson) throws Exception {
        // API Gateway proxy integration delivers the body as a string
        return MAPPER.createObjectNode().put("body", bodyJson);
    }

    @Test
    void validInvoiceReturns200WithNormalizedData() throws Exception {
        String body = "{\"vendor\":\" Acme \",\"invoiceNumber\":\"A-1\",\"invoiceDate\":\"2026-10-01\","
                + "\"subtotal\":100,\"taxAmount\":18,\"total\":118}";
        JsonNode res = handler.handleRequest(event(body), null);
        assertEquals(200, res.get("statusCode").asInt());
        JsonNode out = MAPPER.readTree(res.get("body").asText());
        assertTrue(out.get("valid").asBoolean());
        assertEquals("Acme", out.get("invoice").get("vendor").asText());
        assertEquals("INR", out.get("invoice").get("currency").asText());
    }

    @Test
    void invalidInvoiceReturns422WithErrors() throws Exception {
        String body = "{\"vendor\":\"Acme\",\"invoiceNumber\":\"A-1\",\"invoiceDate\":\"2026-10-01\","
                + "\"subtotal\":100,\"taxAmount\":18,\"total\":500}";
        JsonNode res = handler.handleRequest(event(body), null);
        assertEquals(422, res.get("statusCode").asInt());
        JsonNode out = MAPPER.readTree(res.get("body").asText());
        assertFalse(out.get("valid").asBoolean());
        assertEquals("total must equal subtotal + taxAmount", out.get("errors").get(0).asText());
    }

    @Test
    void garbageBodyReturns400() throws Exception {
        JsonNode res = handler.handleRequest(event("not json"), null);
        assertEquals(400, res.get("statusCode").asInt());
    }

    @Test
    void directInvokeWithObjectBodyAlsoWorks() throws Exception {
        JsonNode ev = MAPPER.readTree("{\"body\":{\"vendor\":\"Acme\",\"invoiceNumber\":\"A-1\","
                + "\"invoiceDate\":\"2026-10-01\",\"subtotal\":100,\"taxAmount\":18,\"total\":118}}");
        assertEquals(200, handler.handleRequest(ev, null).get("statusCode").asInt());
    }
}
