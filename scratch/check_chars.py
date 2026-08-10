s2 = "https://product-launch-agent.myshopify.com/cart/44556677:1?attributes[registration_id]=REG-20260731-EAF80C&attributes[student_name]=Rohan%20Doe&attributes[parent_name]=David%20Doe&checkout[email]=david%40example.com"
print("s2:", s2)
print("'student' in s2:", "student" in s2)
print("'student_name' in s2:", "student_name" in s2)
for i, c in enumerate(s2):
    if c == '[' or c == ']':
        print(f"Index {i}: {c}")
