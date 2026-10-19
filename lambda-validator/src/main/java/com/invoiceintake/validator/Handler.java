package com.invoiceintake.validator;

import com.amazonaws.services.lambda.runtime.Context;
import com.amazonaws.services.lambda.runtime.RequestHandler;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.List;

/**
 * API Gateway (proxy integration) handler. POST body = invoice JSON from the Python service.
 * 200 = valid and normalized, 422 = validation errors, 400 = unreadable body.
 */
public class Handler implements RequestHandler<JsonNode, JsonNode> {

    private static final ObjectMapper MAPPER = new ObjectMapper();
    private final InvoiceValidator validator;

    public Handler() {
        this(new InvoiceValidator());
    }

    Handler(InvoiceValidator validator) {
        this.validator = validator;
    }

    @Override
    public JsonNode handleRequest(JsonNode event, Context context) {
        InvoiceData data;
        try {
            JsonNode body = event.path("body");
            // proxy integration sends the body as a string; direct invokes send an object
            data = MAPPER.readValue(body.isTextual() ? body.asText() : body.toString(), InvoiceData.class);
        } catch (Exception e) {
            return response(400, MAPPER.createObjectNode().put("error", "request body is not valid invoice JSON"));
        }

        List<String> errors = validator.validate(data);
        if (!errors.isEmpty()) {
            ObjectNode out = MAPPER.createObjectNode();
            out.put("valid", false);
            out.set("errors", MAPPER.valueToTree(errors));
            return response(422, out);
        }

        ObjectNode out = MAPPER.createObjectNode();
        out.put("valid", true);
        out.set("invoice", MAPPER.valueToTree(validator.normalize(data)));
        return response(200, out);
    }

    private static JsonNode response(int status, ObjectNode body) {
        ObjectNode r = MAPPER.createObjectNode();
        r.put("statusCode", status);
        r.putObject("headers").put("Content-Type", "application/json");
        r.put("body", body.toString());
        return r;
    }
}
