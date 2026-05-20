package speclink_pkg;

  typedef class speclink_check;

  class speclink_check;
    string requirement_id;
    string check_id;
    bit expected;
    bit observed;
    string result;
    int hit_count;
    int fail_count;
    string messages[$];

    function new(string req_id, string chk_id);
      requirement_id = req_id;
      check_id = chk_id;
      expected = 1;
      observed = 0;
      result = "missing";
      hit_count = 0;
      fail_count = 0;
    endfunction
  endclass

  class speclink_top;
    string project = "{{ project.slug }}";
    string package_version = "generated";
    string current_test;
    speclink_check expected_checks[string];

    function new();
    endfunction

    function void set_current_test(string test_name);
      current_test = test_name;
    endfunction

    task run();
      string plusarg_test;
      if ($value$plusargs("SPECLINK_TESTNAME=%s", plusarg_test)) begin
        set_current_test(plusarg_test);
      end
      start_test(current_test);
    endtask

    function void start_test(string test_name);
      current_test = test_name;
      expected_checks.delete();
{% for test in test_expectations %}
      if (test_name == "{{ test.test_id }}") begin
{% for item in test.checks %}
        expected_checks["{{ item.requirement_id }}::{{ item.check_id }}"] = new("{{ item.requirement_id }}", "{{ item.check_id }}");
{% endfor %}
      end
{% endfor %}
    endfunction

    function void pass_check(string requirement_id, string check_id, string message = "");
      string key = {requirement_id, "::", check_id};
      if (!expected_checks.exists(key)) expected_checks[key] = new(requirement_id, check_id);
      expected_checks[key].observed = 1;
      expected_checks[key].result = "pass";
      expected_checks[key].hit_count++;
      if (message != "") expected_checks[key].messages.push_back(message);
    endfunction

    function void fail_check(string requirement_id, string check_id, string message = "");
      string key = {requirement_id, "::", check_id};
      if (!expected_checks.exists(key)) expected_checks[key] = new(requirement_id, check_id);
      expected_checks[key].observed = 1;
      expected_checks[key].result = "fail";
      expected_checks[key].fail_count++;
      if (message != "") expected_checks[key].messages.push_back(message);
    endfunction

    function void hit_check(string requirement_id, string check_id, string message = "");
      pass_check(requirement_id, check_id, message);
    endfunction

    function void end_test();
      print_summary();
    endfunction

    function void print_summary();
      string key;
      int expected_count = 0;
      int passed_count = 0;
      int failed_count = 0;
      int missing_count = 0;
      bit first_requirement = 1;
      foreach (expected_checks[key]) begin
        expected_count++;
        if (expected_checks[key].result == "pass") passed_count++;
        else if (expected_checks[key].result == "fail") failed_count++;
        else missing_count++;
      end
      $display("=== SPECLINK_SUMMARY_BEGIN ===");
      $display("{");
      $display("  \"schema_version\": \"1.0\",");
      $display("  \"project\": \"{{ project.slug }}\",");
      $display("  \"package_version\": \"%s\",", package_version);
      $display("  \"test\": \"%s\",", current_test);
      $display("  \"status\": \"%s\",", failed_count == 0 ? "passed" : "failed");
      $display("  \"expected_requirements_count\": 0,");
      $display("  \"covered_requirements_count\": 0,");
      $display("  \"expected_checks_count\": %0d,", expected_count);
      $display("  \"passed_checks_count\": %0d,", passed_count);
      $display("  \"failed_checks_count\": %0d,", failed_count);
      $display("  \"missing_checks_count\": %0d,", missing_count);
      $display("  \"requirements\": [");
      foreach (expected_checks[key]) begin
        if (!first_requirement) $display(",");
        first_requirement = 0;
        $write("    {\"id\":\"%s\",\"expected\":true,\"status\":\"%s\",\"checks\":[", expected_checks[key].requirement_id, expected_checks[key].result == "pass" ? "closed" : expected_checks[key].result);
        $write("{\"id\":\"%s\",\"expected\":true,\"observed\":%s,\"result\":\"%s\",\"hit_count\":%0d,\"fail_count\":%0d,\"messages\":[]}", expected_checks[key].check_id, expected_checks[key].observed ? "true" : "false", expected_checks[key].result, expected_checks[key].hit_count, expected_checks[key].fail_count);
        $write("]}");
      end
      $display("");
      $display("  ]");
      $display("}");
      $display("=== SPECLINK_SUMMARY_END ===");
    endfunction
  endclass

endpackage
